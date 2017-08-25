"""
Upload given files to a Dropbox location.

Take filenames or folders as argument, or ask for input if not given.
Upload the files to the given or default location on Dropbox. Perform
a cleanup of any remaining .pyc files unless asked not to. Log 
everything to 'uploadlog.txt' and also print it at runtime.
"""

from __future__ import print_function
import os
import argparse
from datetime import datetime
import dropbox

VERSION = '0.4'


def readylog(logfile=None):
	"""Make the logfile ready for appending."""
	# Open logfile if it is closed, else open 'dbxupload.log'.
	try:
		logfile = open(logfile.name, 'a')
	except AttributeError:
		logfile = open("dbxupload.log", 'a')
	return logfile

def log(msg, priority, verbosity, logfile=None, plain=False):
	"""Log the message according to the priority and verbosity to stdout and logfile.
	
	For verbosity level 0, only error messages are written to stdout.
	For verbosity level 1, error, pass and fail messages are written to stdout.
	For verbosity level 2, all messages are written to stdout.
	Note: Sending logfiles via the parameter seems a bit messy.
	      Do it with rigorous testing.
	"""

	# TODO: Is 'plain' necessary? How about adding it to the priorities?
	selfLogfile = logfile is None or logfile.closed
	# selfLogfile tells whether a new logfile needs to be created.
	logtime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
	# YYYY-MM-DD HH:MM:SS
	if selfLogfile:
		logfile = readylog(logfile)
	priorities = {'INFO': '[*]',  # verbosity levels: 2
	              'PASS': '[+]',  # verbosoty levels: 1, 2
	              'FAIL': '[-]',  # verbosity levels: 1, 2
	              'ERROR': '[!]',
	              'DEBUG': '<|>'} # verbosity levels: 0, 1, 2
	if priority not in priorities:
		raise ValueError("invalid priority specified")
	if verbosity < 0:
		raise ValueError("verbosity level must not be negative")
	if not plain:
		# plain means to not attach anything to the message.
		msg = "[{}] {} {}".format(logtime, priorities[priority], msg)
	if ((verbosity == 0 and priority == 'ERROR')
	    or (verbosity == 1 and priority != 'INFO')
	    or (verbosity >= 2)):
		# See the doc for more info.
		print(msg)
	logfile.write(msg + '\n')
	if selfLogfile:
		# Close the logfile only if it was created in this function.
		# Callers sending their own logfiles are responsible for closing them.
		logfile.close()

def fix_path(path):
	"""Convert paths to the format '/path/to/file'. Empty path is simply ''."""
	if not issubclass(type(path), basestring):
		raise TypeError("fix_path only takes strings and unicodes")
	path = path.replace('\\', '/')
	path = '/'.join(i for i in path.split('/') if i)
	if path:
		path = '/' + path
	return path

def upload(dbxconn, files, location='/', pps=False, clean=False, replace=False, verbosity=1):
	"""Upload the files and folders to remote with the given connection."""
	# logfile = readylog()
	location = fix_path(location)
	log('\n' + r"\\\\\\\\\\\\\\\ Session started ///////////////", 'INFO',
	    verbosity, plain=True)
	if not isinstance(dbxconn, dropbox.Dropbox):
		# If dbxconn is a token...
		dbxconn = openDropbox(dbxconn)
	metadata = {}
	for filename in files:
		filename = fix_path(filename)
		if pps:
			# To preserve path structure, add the root directory to the location.
			# To get the root, reverse 'filename', get the part after first '/',
			# and reverse it again.
			new_location = ''.join([location, filename[::-1].split('/', 1)[1][::-1]])
		else:
			new_location = location
		if os.path.isfile(filename[1:]): # The first char must be '/'.
			if clean:
				cleanup(filename[1:], verbosity)
			metadata[filename] = ulfile(dbxconn, filename, new_location, replace, verbosity)
		elif os.path.isdir(filename[1:]):
			if clean:
				cleanup(filename[1:], verbosity)
			metadata.update(ulfolder(dbxconn, filename, new_location, replace, verbosity))
		else:
			log("Could not locate the file: " + filename, 'FAIL', verbosity)
	log(r"//////////////// Session ended \\\\\\\\\\\\\\\\", 'INFO',
	    verbosity, plain=True)
	# logfile.close()
	return metadata

def ulfile(dbxconn, filename, location='/', replace=False, verbosity=1):
	"""Upload file to the remote location."""
	# logfile = readylog()
	curdir = os.getcwd()
	if filename.count('/') > 1:
		# If 'filename' is a path, go to the path and upload the file.
		# To get the path, reverse 'filename', get the part after first '/',
		# and reverse it again.
		os.chdir(filename[1:][::-1].split('/', 1)[1][::-1]) # Find a better way
		filename = fix_path(filename.split('/')[-1])
	try:
		data = open(filename[1:], 'rb')
	except OSError:
		os.chdir(curdir)
		log("Couldn't open file \"{}\"".format(filename), 'FAIL', verbosity)
		# logfile.close()
		return None
	os.chdir(curdir)
	log("Opened \"{}\"".format(filename), 'INFO', verbosity)
	log("Uploading \"{}\"".format(filename), 'INFO', verbosity)
	# log("replace value is {}".format(str(replace)), 'DEBUG', 2) # DEBUG
	filemetadata = dbxconn.files_upload(data.read(), location + filename,
	                mode=(dropbox.files.WriteMode.overwrite if replace
	                      else dropbox.files.WriteMode.add),
	                autorename=not(replace))
	log("Uploaded \"{}\" to \"remote://{}\"".format(filename, filemetadata.path_display),
	    'PASS', verbosity)
	data.close()
	# logfile.close()
	return filemetadata


def ulfolder(dbxconn, foldername, location='/', replace=False, verbosity=1):
	"""Upload folder to the remote location."""
	metadata = {}
	log("Uploading folder \"{}\"".format(foldername), 'INFO', verbosity)
	log("Foldername is {}".format(foldername), 'DEBUG', 2)
	for rootdir, subdirs, files in os.walk(foldername[1:], topdown=False):
		log("{}, {}, {}".format(rootdir, subdirs, files), 'DEBUG', 2)
		for file in files:
			filepath = fix_path(os.path.join(rootdir, file))
			new_location = fix_path(location) + fix_path(rootdir)
			log("Filepath is {}. Location is {}.".format(filepath, new_location), 'DEBUG', 2)
			metadata[filepath] = ulfile(dbxconn, filepath, new_location, replace, verbosity)
	log("Uploaded folder \"{}\" to \"remote://{}\"".format(foldername, location),
	    'PASS', verbosity)
	return metadata


def cleanup(filename, verbosity):
	"""Remove .pyc files. 'filename' can be a file or a folder."""
	# TODO: Use a regex string to match what to clean.
	if filename.endswith('.py') and os.path.isfile(filename + 'c'):
		filename += 'c'
		try:
			os.remove(filename)
			log("Removed \"{}\"".format(filename), 'INFO', verbosity)
			return 1
		except OSError as e:
			log("Error while removing \"{}\": {}".format(filename, e),
			    'INFO', verbosity)
			return -1
	elif os.path.isdir(filename):
		cleaned = []
		for rootdir, subdirs, files in os.walk(filename):
			for file in files:
				cleaned.append(cleanup(os.path.join(rootdir, file), verbosity))
		return -1 if -1 in cleaned else 1
	else:
		return 0

def openDropbox(token=None):
	"""Open a Dropbox connection using the given token."""
	if token is None:
		with open('dbx.cfg') as cfg:
			# Token is read from 'dbx.cfg' below the line '-t'.
			found = False
			for line in cfg:
				if found:
					token = line.strip()
					break
				found = (line.strip() == '-t')
	dbx = dropbox.Dropbox(token)
	# Check validity of token and raise appropriate errors.
	dbx.users_get_current_account()
	return dbx

def main():
	"""main() function for dbxuploader.py"""
	desc = """
Upload given files to a Dropbox location.

Note: the options can also be provided by storing them in a file and supplying
the filename as an argument prefixed with '@', like so: dbxuploader.py @dbx.cfg.
It can also be combined with other arguments that come before it.
"""
	parser = argparse.ArgumentParser(description=desc.split('\n\n')[0],
	                                 epilog=desc.split('\n\n', 1)[1],
	                                 fromfile_prefix_chars='@')
	parser.add_argument("files", nargs="+",
	                    help="Names of one or more folders or files to upload",
	                    metavar='FILENAME')
	parser.add_argument('-t', "--token",
	                    help="Private token of a Dropbox app")
	parser.add_argument("-l", "--location", default="/",
	                    help="Location of remote destination")
	parser.add_argument('-r', "--replace", action="store_true",
	                    help="Replace remote files if they already exist")
	parser.add_argument("--pps", action="store_true",
	                    help="Preserve path structures of files and folders")
	parser.add_argument("-c", "--cleanup", action="store_true",
	                    help="Remove the respective .pyc files from physical disk "
	                         "(without uploading)")
	parser.add_argument('-v', "--verbosity", type=int, default=1, choices=[0, 1, 2],
	                    help="Set verbosity level to none(0), partial(1) or full(2)")
	parser.add_argument('-V', "--version", action='version',
	                    version="dbx-uploader v"+VERSION)
	args = parser.parse_args()

	# dbxconn = openDropbox(args.token)
	# print(args)
	try:
		upload(args.token, args.files, args.location, args.pps,
		       args.cleanup, args.replace, args.verbosity)
	except KeyboardInterrupt:
		log("Script interrupted by user.", 'ERROR', args.verbosity)
		log(r"/////////////// Session  failed \\\\\\\\\\\\\\\ ", 'INFO',
		    args.verbosity, None, True)
	except Exception as ex:
		log("Error: " + str(ex), 'ERROR', args.verbosity)
		log(r"/////////////// Session  failed \\\\\\\\\\\\\\\ ", 'INFO',
		    args.verbosity, None, True)

if __name__ == '__main__':
	import sys
	sys.exit(main())
