"""Instantiate fixed-width assembly-time test constants without changing code/tables."""
import struct
class Template:
    def __init__(self,path):
        self.data=path.read_bytes()
        if self.data[:7]!=b'\x7fELF\x01\x01\x01':raise ValueError('Expected little-endian ELF32')
        off=struct.unpack_from('<I',self.data,32)[0];stride,n=struct.unpack_from('<HH',self.data,46)
        sections=[struct.unpack_from('<10I',self.data,off+i*stride) for i in range(n)]
        symbols={}
        for section in sections:
            if section[1]!=2:continue
            strings=sections[section[6]];names=self.data[strings[4]:strings[4]+strings[5]]
            for i in range(section[4],section[4]+section[5],section[9]):
                name,value,size,info,other,index=struct.unpack_from('<IIIBBH',self.data,i)
                if not name or not 0<index<n:continue
                key=names[name:names.index(b'\0',name)].decode()
                target=sections[index];symbols[key]=target[4]+value-target[3]
        self.input=symbols['input_vector'];self.expected=symbols['expected_length']
        assert self.data[self.input+14]==0
    def instantiate(self,vector,expected):
        if len(vector)!=14 or not vector.isascii() or not vector.isdigit():raise ValueError(vector)
        out=bytearray(self.data);out[self.input:self.input+15]=vector.encode()+b'\0';struct.pack_into('<i',out,self.expected,expected)
        return out
