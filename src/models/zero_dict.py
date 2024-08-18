class ZeroDict(dict):
    def __getitem__(self, key):
        return super().__getitem__(key) if key in self else 0

    def get(self, key, *args):
        if args:
            return super().__getitem__(key) if key in self else args[0]
        return super().__getitem__(key) if key in self else 0

