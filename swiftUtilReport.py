from os.path import basename
import requests
import json
import datetime
import time
import calendar
import sys
import csv
from collections import namedtuple
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
import smtplib

data = {}
d1 = datetime.datetime.now()
sender = "test@noname.dev"
smtpserver="smtp.noname.dev"

def toDate(timestamp):
    value = datetime.datetime.fromtimestamp(timestamp / 1000)
    return value.strftime('%Y-%m-%d')

def toTime(timestamp):
    value = datetime.datetime.fromtimestamp(timestamp / 1000)
    return value.strftime('%H:%M:%S')

def add_months(sourcedate, months, delimeter=''):
    """ ex) add_months(datetime.date.today(), 1)
    """
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month / 12
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year, month)[1])
    return datetime.date(year, month, day).strftime("%Y" + delimeter + "%m" + delimeter + "%d")

def date2timestamp(YYYY, MM, DD):
    return str(time.mktime(datetime.date(int(YYYY), int(MM), int(DD)).timetuple())).replace('.0', '000')

def getQueryIdx(input_json):
    queries = {}
    input_json = input_json  # [:-1]
    loaded = json.loads(input_json)
    i = 0
    try:
        while True:
            x = loaded['facets'][str(i)]['facet_filter']['fquery']['query']['filtered']['query']['query_string'][
                'query']
            queries[str(i)] = x
            i += 1
    except BaseException, e:
        pass
    return queries

def getIdx(dic, key):
    return dic[key]

def setVar(text, old, to):
    return text.replace('${' + old + '}', to)

def main(json_input=None, csv_output=None, receiver=None):
    with open(json_input, "rb") as f_in:
        request = f_in.read()
        
    from_date = add_months(datetime.date.today(), -1)[:-2] + '01'
    to_date = add_months(datetime.date.today(), 0)[:-2] + '01'
    
    mail_title = 'test mail - ' + from_date[:-2]
    csv_output = 'output' + from_date[:-2] + '.csv'
    
    curl_request = request.split("' -d '")
    p = curl_request[0].find("-XGET ")
    
    url = curl_request[0][p + 7:]
    url = url.replace('${YYYY}', from_date[:4])
    url = url.replace('${MM}', from_date[4:6])
    
    request = curl_request[1].strip()[0:-1]
    request = request.replace('${FROM}', date2timestamp(from_date[:4], from_date[4:6], from_date[6:]))
    request = request.replace('${TO}', date2timestamp(to_date[:4], to_date[4:6], to_date[6:]))
    
    queryIdx = getQueryIdx(request)
    response = requests.post(url, data=request)
    response_json = json.loads(response.text)
    
    if "facets" in response_json:
        i = 0
        with open(csv_output, "wb") as f_out:
            writer = csv.writer(f_out)
            try:
                writer.writerow(['date', 'account', 'bytes(max)'])
                while True:
                    if response_json["facets"][str(i)]["entries"]:
                        for x in response_json["facets"][str(i)]["entries"]:
                            writer.writerow(
                                [toDate(x['time']), queryIdx[str(i)], x['max']])
                    i = i + 1
            except Exception, e:
                # print e
                pass

    # send mail
    receivers = []
    mail_body = "B2B Swift Montly Usage mail"
    with open(receiver, "rb") as f_in_mail:
        receiver = f_in_mail.readline()
        funcSendmail(title=mail_title, receiver=receiver, body=mail_body, attachment_list=[csv_output])

def funcSendmail(title, receiver, body, attachment_list):
    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = receiver
    msg["Subject"] = title

    # body=""
    for attachment in attachment_list:
        # body+='<img src="cid:' + attachment + '.jpg"><br>'
        # with open(attachment, 'rb') as fp:
        #        img = MIMEImage(fp.read())

        with open(attachment, "rb") as fil:
            part = MIMEApplication(open(attachment, "rb").read())
            part.add_header('Content-Disposition', 'attachment', filename=attachment)
            msg.attach(part)

        # img.add_header('Content-ID', attachment)
        # msg.attach(img)

        msgText = MIMEText(body, 'html')
        msg.attach(msgText)  # Added, and edited the previous line

        # for attachment in attachment_list['list'].split() :
        #        fp = open(attachment+'.jpg', 'rb')
        #        img = MIMEImage(fp.read())
        #        fp.close()
        #        img.add_header('Content-ID', attachment)
        #        msg.attach(img)

        #print msg.as_string()

        s = smtplib.SMTP(smtpserver)
        s.sendmail(msg["From"], msg["To"], msg.as_string())
        s.quit()


if __name__ == "__main__":

    input_file = None
    output_file = None

    for arg in sys.argv:
        if arg.find('=') > 0:
            strArg = arg.split('=')

            if str(strArg[0]).lower() == '--in':
                input_file = str(strArg[1])

            if str(strArg[0]).lower() == '--out':
                output_file = str(strArg[1])

    now = str(datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))

    # if not input_file or not output_file:
    #     print 'USAGE: python swiftUtilReport.py --in=[REQ_QUERY]'
    #     exit(1)

    main(json_input='swiftUtilReport.json', receiver='swiftUtilReport.conf')
