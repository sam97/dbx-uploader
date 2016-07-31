import argparse
import dropbox
from datetime import datetime
from os import path, remove

VERSION = '0.2'

"""
A script that takes filename(s) that is to be uploaded as argument,
along with an optional location in the Dropbox folder. It is not verbose and
all logs are stored in uploadlog.txt.

Usage: uploader.py [-h] [-l LOCATION] [-c] [FILENAME [FILENAME ...]]

positional arguments:
  FILENAME              take one or more files to upload

optional arguments:
  -h, --help            show this help message and exit
  -l LOCATION, --location LOCATION
						location of remote destination (start and end with
						'/')
  -c, --cleanup         don't clean the respective .pyc files
"""

parser = argparse.ArgumentParser()
parser.add_argument("files", nargs="*",
					help="take one or more files to upload", metavar='FILENAME')
parser.add_argument("-l", "--location", default="/",
					help="location of remote destination (start and end with '/')")
parser.add_argument("-c", "--cleanup", action="store_false",
					help="don't clean the respective .pyc files")
args = parser.parse_args()

files = args.files
if files == None:
	files = [i.split('\\')[-1]
			 for i in raw_input("Filnames seperated by \"\\\\\"): \n").split('\\\\')]

TOKEN = "<token-number>"
# TOKEN = "<testing-token-number"
dbx = dropbox.Dropbox(TOKEN)

logfile = open("uploadlog.txt", 'a')
logfile.write("=============== New session started ===============\n")
for filename in files:
	try:
		data = open(filename)
		logfile.write(
			"[{0}] [+] Opened \"{1}\"\n".format(datetime.now(), filename))
	except Exception as e:
		logfile.write(
			"[{0}] [-] Error while opening \"{1}\"\n".format(datetime.now(), filename))
		logfile.write("[{0}] [*] Error: {1}", datetime.now(), e)
		print "Error"
		data.close()
		continue
	try:
		dbx.files_upload(data.read(), args.location + filename,
						 mode=dropbox.files.WriteMode.overwrite, autorename=False)
		logfile.write("[{0}] [+] Uploaded \"{1}\" to \"Dropbox{2}\"\n".format(
			datetime.now(), filename, args.location))
		print "Done"

	except Exception as e:
		logfile.write("[{0}] [-] Error while uploading \"{1}\" to \"Dropbox{2}\"\n".format(
			datetime.now(), filename, args.location))
		logfile.write("[{0}] [*] Error: {1}", datetime.now(), e)
		print "Error"
	try:
		if args.cleanup and path.isfile(filename):
			filename += 'c'
			remove(filename)
			logfile.write(
				"[{0}] [+] Removed \"{1}\"\n.".format(datetime.now(), filename))
			print "Removed"
	except Exception as e:
		logfile.write(
			"[{0}] [-] Error while removing \"{1}\".\n".format(datetime.now(), filename))
		logfile.write("[{0}] [*] Error: {1}\n".format(datetime.now(), e))
		# print "Error"
	data.close()

logfile.write("END OF SESSION\n\n")
logfile.close()
