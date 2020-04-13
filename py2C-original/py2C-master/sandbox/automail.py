# a lot of imports ...
import smtplib
import imaplib
import email
import email.header
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
# multiprocessing and timing
import multiprocessing as mp
import time
# mathematical stuff
import numpy as np
import matplotlib.pyplot as plt


def mail_listener_process(account,readQ,writeQ,*args):
    " Defines the continuous process of listening to an email account, picking \
    up new email and acting on it, if they match the correct pattern. I.e. \
    puts the first word of the email text body and the sender's address into \
    writeQ. This process can be controlled via its readQ."
    
    # deal with inputs
    config = {'subject':'RPi request','period':10}
    if len(args) > 0 and type(args[0]) == dict:
        kwargs = args[0]
    else:
        kwargs = dict()
    for kw in kwargs: config[kw] = kwargs[kw]
    
    # target imap server
    imap = imaplib.IMAP4_SSL(account['imap'],account['imap_port'])
    imap.login(account['user'],account['pwd']) # login
    
    # initialize
    (Done, Send, last, data,) = (False, False, 0, [],)
    start = time.time()
    
    # listening loop
    while not Done:
        # Read new data from device and pair with current time.
        now = time.time() - start
        imap.select(mailbox='INBOX') # Select inbox or default namespace
        # find all unseen mails
        #res, data = imap.search(None,'(SUBJECT "%s")' % config['subject'])
        #res, data = imap.search(None,'Subject','RPi request')
        res, data = imap.search(None,'(UNSEEN)')
        # writeQ.put((data[0].split(),res,))
        writeQ.put('tic')
        if res == 'OK':
            # cycle through new emails
            for num in data[0].split():
                # fetch email (sets flag '\Seen')
                rv, data = imap.fetch(num,'RFC822')
                # read message from string
                msg = email.message_from_string(data[0][1])
                
                # decode subject line to unicode string
                subject = unicode(email.header.decode_header(msg['Subject'])[0][0])
                # check whether subject matches
                #writeQ.put("-"+subject.lower()+"-")
                if subject.lower() != config['subject'].lower():
                    continue
                
                # search for plain-text content in the message body
                if msg.is_multipart():
                    for part in msg.walk():
                        # find (first) part with plain text and decode
                        if part.get_content_type() in ('text/plain',):
                            text = part.get_payload(decode=True) 
                            break
                else:
                    text = msg.get_payload(decode=True)
                
                # check that the search for text in the mail returned a result
                # take only the first word and pick out address to send response
                if len(text) != 0:
                    kw = text.split()[0]
                    from_addr = msg['From']
                else: 
                    continue
                
                # write results to writeQ
                writeQ.put((kw,from_addr,))
                
                res, data = imap.store(num,'+FLAGS','\\Seen')
        
        last = now        
        # wait to maintain minimal check period
        while (time.time()-start-last) < config['period']:
            pass
        
        # check readQ for any commands
        if not readQ.empty():
            cmd = readQ.get()
            assert cmd.__class__ == str
            assert len(cmd) >= 4
            if cmd[:4] == "done":
                # Exits the loop.
                Done = True
            elif cmd[:4] == "else":
                pass
            Done = True        
                
    imap.close()
    #writeQ.put("Listening process ended.")
    
def send_data_as_response(cmd,to_addr,account):
    " Sends a data plot as response. "
    
    # pick data file
    datafile = 'data.txt'
    pngfile = 'test.png'
    
    # Create the container (outer) email message.
    msg = MIMEMultipart()
    msg['Subject'] = 'RPi response'
    # me == the sender's email address
    # family = the list of all recipients' email addresses
    msg['From'] = account['user']
    msg['To'] = to_addr
    msg.attach(MIMEText('This is an automatic reply. See attachment for plot.'))   
    
    # load data from text file
    with open(datafile,'rb') as f:
        txt_data = f.read()
    data = [[float(val) for val in line.split(",")] \
            for line in txt_data.split("\n")]
    
    # plot with matplotlib, save as png, attach png to msg
    fig = plt.figure()
    plt.plot([el[0] for el in data],[el[1] for el in data],'-k',\
             [el[0] for el in data],[el[2] for el in data],'-r',\
             [el[0] for el in data],[el[3] for el in data],'-b')
    fig.savefig(pngfile,dpi=600)
    
    with open(pngfile, 'rb') as fp:
        img = MIMEImage(fp.read())
    msg.attach(img)
    
    # send mail
    #try:
    smtp = smtplib.SMTP(account['smtp'],account['smtp_port'])
    smtp.ehlo()
    smtp.starttls()
    smtp.login(account['user'],account['pwd'])
    smtp.sendmail(msg['From'],msg['To'],msg.as_string())
    smtp.close()
    print 'Sent response to {}.'.format(to_addr)
    #except:
    #    print "Failed to send mail!"  

if __name__ == "__main__":
    # windows executables need freeze support for multiprocessing
    mp.freeze_support()
    
    # set up imap server to read inbox
    # (low security -- may want to improve this in the 
    # future to read from encrypted file)
    account = {'user':'thywissenlab.rpi02@gmail.com',\
               'pwd':'c7ld4toms',\
               'imap':'imap.gmail.com',\
               'imap_port':'993',\
               'smtp':'smtp.gmail.com',\
               'smtp_port':587,\
               }
    
    # initialize readQ, writeQ and listening process 
    # (which obviously sees readQ and writeQ swapped)
    readQ = mp.Queue()
    writeQ = mp.Queue()
    listener = mp.Process(target=mail_listener_process, \
                          args=(account,writeQ,readQ,))
    
    # start the listener process
    listener.start()
    
    # quick and dirty: finite loop (to make sure multiprocessing does not run forever)
    cnt = 0
    while cnt < 12:
        cnt += 1
        # wait till something is recieved
        while readQ.empty():
            pass
        # read one entry from readQ
        read = readQ.get()
        # show what was recieved @@ debugging
        print("{:04}: {}".format(cnt,read))
        
        if type(read) == tuple and len(read) > 1:
            print("sending?")
            send_data_as_response(read[0],read[1],account)
        
    writeQ.put("done")
        
    print("waiting")
    listener.join()
        
    print("outside")
