"""Handshake before the trusted foreground command starts; no state access."""
import os
import sys
fd=int(sys.argv[1])
if os.read(fd,1)!=b'1':sys.exit(125)
os.close(fd)
os.execvpe(sys.argv[2],sys.argv[2:],os.environ)
