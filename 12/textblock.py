
from io import FileIO, BufferedIOBase, BufferedReader, TextIOBase, TextIOWrapper, StringIO
import gzip
from typing import Union


class TextBlockReader(object):

    def __init__(self, f:Union[str, BufferedIOBase, TextIOBase]) -> None:
        if isinstance(f, str):                   # if this is a file name or the block(s) packed in str,
            if '\n' in f:                    # has newline(s) in it
                self.f = StringIO(f)              # this is definitelly the block itself
                self.f.seek(0)                    # park at the beginning!
            else:
                self.f = self.gzadapt(open(f, 'rb')) # f is filename -> open it (whether its gzipped or not)
        else:
            self.f = f
        self.collect = False
        self.line:str = None

    @staticmethod
    def gzadapt(f: BufferedReader) -> BufferedReader:
        signature = f.read(2)
        f.seek(0)
        if signature == b'\x1f\x8b':
            f = gzip.open(f, 'r')
        return f

    def readline(self) -> str:
        if isinstance(self.f, TextIOBase): return self.f.readline()
        if isinstance(self.f, BufferedIOBase): return self.f.readline().decode('utf-8')
        return None

    def readBlock(
        self,
        blockStartDelim:str = None,
        blockEndDelim:str = None,
        header:str = None,
        footer:str = None
    ) -> Union[StringIO, None]:
        """Reads a block of text bounded by a start and end delimiters,
        or at least one of them. Returns the resulting block as a
        StringIO object, which in turn, can be read line by line

        Args:
            blockStartDelim (str, optional): starting delimiter. Defaults to None.
            blockEndDelim (str, optional): ending delimiter. Defaults to None.
            header (str, optional): text elements to be appended as header part. Defaults to None.
            footer (str, optional): text elements to be appended as footer part. Defaults to None.

        Returns:
            Union[StringIO, None]: StringIO object, unless EOF reached
        """
        block = StringIO()
        if self.line is None:
            self.line = self.readline()
        while(self.line):
            #print('  ###line###', self.line)
            if not self.collect:                             # hasn't started collecting yet...
                if blockStartDelim is None:                  #  formats without start delimiter
                    self.collect = True                      #   start collecting block immediatelly
                    #print('>>>')
                    if header is not None:
                        block.write(header + '\n')
                    block.write(self.line)
                elif self.line.startswith(blockStartDelim):  #  formats with start delimiter
                    self.collect = True                      #   start collecting block
                    #print('>>>')
                    if header is not None:                   #    as soon as delimiter encountered
                        block.write(header + '\n')
                    block.write(self.line)
            elif blockEndDelim is not None:                  # collecting from block with end delimiter
                if not blockEndDelim in self.line:           #  already inside block and collecting
                    block.write(self.line)                   #   
                else:
                    block.write(self.line)                   #  until we hit an end delimiter
                    self.line = None                         #   reset lien after writing last one
                    if footer is not None:
                        block.write(footer + '\n')
                    block.seek(0)                            # point to the start
                    self.collect = False
                    #print('<<<')
                    return block                             # return StringIO
            elif blockEndDelim is None:                      # block end delimiter is not set
                if not self.line.startswith(blockStartDelim):# so we shall search for the start delimiter 
                    block.write(self.line)                   # of the next block
                else:
                    if footer is not None:                   # we preserve the line containing start delimiter
                        block.write(footer + '\n')           # to be consumed for the next block
                    block.seek(0)
                    self.collect = False
                    #print('<<<')
                    return block
            self.line = self.readline()
        if blockEndDelim is None and self.collect:          # prepare and return the last block
            if footer is not None:
                block.write(footer + '\n')
            block.seek(0)
            self.collect = False
            #print('<<<')
            return block    
        return None

