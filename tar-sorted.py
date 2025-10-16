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
        self.mode = mode
        self.file = file
        self.verbose = verbose
        assert self.mode in ("print", "print0")
        # Collect entries; md5 will be computed later only for same-size files
        # entry tuple: (dirname, basename, ext, size, is_reg, path)
        self.entries = []

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
            is_reg = stat.S_ISREG(st.st_mode)
            size = st.st_size if is_reg else None
            self.entries.append((dirname, basename, ext, size, is_reg, path))

    def process(self):
        def sort_key(x):
            return x[2], x[1], x[0] # ext, basename, dirname

        # Group regular files by size so we only hash potential duplicates
        by_size = {}
        for dirname, basename, ext, size, is_reg, path in self.entries:
            if is_reg:
                by_size.setdefault(size, []).append((dirname, basename, ext, size, is_reg, path))

        # Assign md5 keys:
        # - regular files with a unique size -> unique sentinel per path (no hashing)
        # - regular files with duplicate size -> compute real md5
        # - non-regular files -> md5 key = None (same as original behavior)
        by_md5 = {}
        records = []  # (dirname, basename, ext, md5_key, path)

        for dirname, basename, ext, size, is_reg, path in self.entries:
            if not is_reg:
                md5_key = None
            else:
                group = by_size.get(size, [])
                if len(group) <= 1:
                    md5_key = ("solo", path)  # unique sentinel, avoids hashing
                else:
                    md5_key = read_md5(path)
            by_md5.setdefault(md5_key, []).append(path)
            records.append((dirname, basename, ext, md5_key, path))

        # Sort by ext/basename/dirname, then emit first time we see each md5_key
        seen = set()
        for _, _, _, md5_key, _ in sorted(records, key=sort_key):
            if md5_key not in seen:
                seen.add(md5_key)
                for p in sorted(by_md5[md5_key]):
                    self.emit(p)

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
