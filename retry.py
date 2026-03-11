#!/usr/bin/env python3
"""retry - Retry a command on failure. Zero deps."""
import sys,subprocess,time
def main():
    if len(sys.argv)<2:print('Usage: retry.py [-n N] [-d secs] <cmd>');sys.exit(1)
    n=3;delay=1;cmd_start=1
    if '-n' in sys.argv:i=sys.argv.index('-n');n=int(sys.argv[i+1]);cmd_start=max(cmd_start,i+2)
    if '-d' in sys.argv:i=sys.argv.index('-d');delay=float(sys.argv[i+1]);cmd_start=max(cmd_start,i+2)
    cmd=' '.join(sys.argv[cmd_start:])
    for attempt in range(1,n+1):
        r=subprocess.run(cmd,shell=True)
        if r.returncode==0:sys.exit(0)
        if attempt<n:print(f'Attempt {attempt}/{n} failed, retrying in {delay}s...',file=sys.stderr);time.sleep(delay)
    print(f'Failed after {n} attempts',file=sys.stderr);sys.exit(1)
if __name__=='__main__':main()
