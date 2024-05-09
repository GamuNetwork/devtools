import argparse

def decode(msg : str):
    return bytes.fromhex(msg).decode()

def encode(msg : str):
    return msg.encode().hex()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Decode a message')
    parser.add_argument('msg', help='Message to decode or encode')
    parser.add_argument('-e', '--encode', action='store_true', help='Encode the message instead of decoding it')
    args = parser.parse_args()
    
    if args.encode:
        print(encode(args.msg))
    else:
        print(decode(args.msg))
