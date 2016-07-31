import argparse
import dropbox
from datetime import datetime
import os

desc = """
Upload given files to a Dropbox location.

Take filenames or folders as argument, or ask for input if not given.
Upload the files to the given or default location on Dropbox. Perform
a cleanup of any remaining .pyc files unless asked not to. Log 
everything to 'uploadlog.txt' and also print it at runtime.
"""

parser = argparse.ArgumentParser(description=desc.split('\n\n')[0], epilog=desc.split('\n\n')[-1])
parser.add_argument("files", nargs="*",
                    help="names of one or more folders or files to upload", metavar='FILENAME')
# :: todo: verbosity arguments
parser.add_argument("-l", "--location", default="/",
                    help="location of remote destination", metavar='/LOCATION/')
parser.add_argument("-c", "--cleanup", action="store_false",
                    help="don't clean the respective .pyc files")
args = parser.parse_args()



def log(msg, stdinv=True, filev=True):
	msg = "[{}] ".format(str(datetime.now())[:-7]) + msg
	if stdinv:
		print msg
	if filev:
		logfile.write(msg)
	return msg

def keyintr(func):
	# :: todo: implement this function throughout script.
	log("[-] Halt: User interrupted the script while \"{}\".".format(func))
	logfile.write("END OF SESSION\n\n")
	logfile.close()

def ulfile(filename, location=args.location, verbose=True, ignorepyc=True):
	if ignorepyc and filename.endswith('.pyc'):
		log("[*] Ignoring \"{}\".\n".format(filename), verbose)
		return None

	try:
		data = open(filename)
		log("[+] Opened \"{}\"\n".format(filename), verbose)
	except KeyboardInterrupt:
		data.close()
		keyintr("opening file")
	except Exception as e:
		log("[-] Error while opening \"{}\"\n{}[*] Error: {}\n".format
		    (filename,' ' * 22, e), True)
		data.close()
		return None

	log("[*] Uploading \"{}\"\n".format(filename), verbose)

	try:
		filemetadata = dbx.files_upload(data.read(), location + filename,
		                                mode=dropbox.files.WriteMode.overwrite, autorename=False)
		log("[+] Uploaded \"{}\" to \"Dropbox{}\"\n".format(filename,
		                                                    location), verbose)
	except KeyboardInterrupt:
		data.close()
		keyintr("uploading file")
	except Exception as e:
		log("[-] Error while uploading \"{0}\" to \"Dropbox{1}\"\n{2}[*] Error: {3}\n".format(
			filename, args.location, ' ' * 22, e), True)
		filemetadata = None
	finally:
		data.close()
		return filemetadata


def ulfolder(foldername, location=args.location, verbose=False):
	metadata = {}
	log("[*] Uploading folder \"{}\"...\n".format(foldername), verbose)
	for rootdir, subdirs, files in os.walk(foldername, topdown=False):
		for file in files:
			filepath = os.path.join(rootdir, file).replace('\\', '/')
			metadata[filepath] = ulfile(filepath, location, verbose)
	return metadata


def cleanup(filename, verbose=True):
	if os.path.isfile(filename + 'c'):
		filename += 'c'
		try:
			os.remove(filename)
			log("[+] Removed \"{}\".\n".format(filename), verbose)
			return 1
		except Exception as e:
			log("[-] Error while removing \"{}\".\n{}[*] Error: {}\n".format
			    (filename,  ' ' * 22, e), verbose)
			return -1
	elif os.path.isdir(filename):
		cleaned = []
		for rootdir, subdirs, files in os.walk(filename):
			for file in files:
				cleaned.append(cleanup(os.path.join(rootdir, file)))
		return -1 if -1 in cleaned else 1
	else:
		return 0


files = args.files
if files == None:
	files = [i.split('\\')[-1]
	         for i in raw_input("Filenames seperated by \"\\\\\": \n").split('\\\\')]

TOKEN = "<token-number>"
# TOKEN = "<testing-token-number>"
dbx = dropbox.Dropbox(TOKEN)

logfile = open("uploadlog.txt", 'a')
logfile.write("=============== New session started ===============\n")
# logfile.write("=============== Test session started ===============\n")
for filename in files:
	log("[*] Checking \"{}\"...\n".format(filename))
	# try:
	# 	# Wait in case the user wants quit.
	# 	time.sleep(3)
	# except KeyboardInterrupt:
	# 	keyintr("checking file")
	# 	import sys
	# 	sys.exit(0)
	if os.path.isfile(filename):
		ulfile(filename)
	elif os.path.isdir(filename):
		ulfolder(filename)
	else:
		log("[-] Error: Could not find any file or folder with the name \"{}\".\n".format(filename))
		continue

	if args.cleanup:
		cleanup(filename)

logfile.write("END OF SESSION\n\n")
logfile.close()


# def main():
# if __name__ == '__main__':
	# main()
