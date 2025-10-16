#!/usr/bin/env python3
import sys, os, stat, hashlib

def read_md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        while True:
            b = f.read(1048576)
            if not b:
                break
            h.update(b)
    return h.digest()

class Tree:
    def __init__(self, mode="print", file=sys.stdout, verbose=False):
        self.files = {} # md5: [(dirname, basename, ext, md5, path)]
        self.mode = mode
        self.file = file
        self.verbose = verbose
        assert self.mode in ("print", "print0")

    def emit(self, path):
        self.file.write(path)
        self.file.write("\0" if self.mode == "print0" else "\n")

    def scan(self, path):
        st = os.lstat(path)
        if stat.S_ISDIR(st.st_mode):
            self.emit(os.path.join(path, ""))
            for item in os.listdir(path):
                self.scan(os.path.join(path, item))
        else:
            dirname, basename = os.path.split(path)
            ext = os.path.splitext(basename)[1].lower()
            if stat.S_ISREG(st.st_mode):
                md5 = read_md5(path)
            else:
                md5 = None
            self.files.setdefault(md5, []).append(
                (dirname, basename, ext, md5, path))

    def process(self):
        def sort_key(x):
            return x[2], x[1], x[0] # ext, basename, dirname

        # Sort by extension, but emit all files with the same MD5 together
        md5s = set()
        for _, _, _, md5, _ in sorted(
                (y for x in self.files.values() for y in x), key=sort_key):
            if md5 not in md5s:
                md5s.add(md5)
                # emit all paths with the same md5
                for path in sorted(
                        (path for _, _, _, _, path in self.files[md5])):
                    self.emit(path)

    def close(self):
        pass

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="sort files to improve tar compression")
    parser.add_argument("-0", dest="nul", action="store_true",
                        help="like -print0")
    parser.add_argument("-o", metavar="output", help="output file")
    parser.add_argument("-v", action="store_true", help="verbose mode with -c")
    parser.add_argument("paths", nargs="+")
    args = parser.parse_args()

    mode = "print0" if args.nul else "print"

    if args.o:
        file = open(args.o, "w")
    else:
        file = sys.stdout

    tree = Tree(mode, file, verbose=bool(args.v))
    for path in args.paths:
        tree.scan(path)
    tree.process()
    tree.close()
    if args.o:
        file.close()

if __name__ == "__main__":
    main()
