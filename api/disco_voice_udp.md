# disco.voice.udp







## Constants


{'type': 'assign', 'targets': ['MAX_TIMESTAMP'], 'value': 4294967295}



{'type': 'assign', 'targets': ['MAX_SEQUENCE'], 'value': 65535}





## Classes

### UDPVoiceClient


_Inherits From `LoggingClass`_








#### Functions



#### __init__(<code>self, <code>vc</code>)








#### increment_timestamp(<code>self, <code>by</code>)








#### setup_encryption(<code>self, <code>encryption_key</code>)








#### send_frame(<code>self, <code>frame, <code>sequence, <code>timestamp=None, <code>incr_timestamp=None</code>)








#### run(<code>self</code>)








#### send(<code>self, <code>data</code>)








#### disconnect(<code>self</code>)








#### connect(<code>self, <code>host, <code>port, <code>timeout, <code>addrinfo=None</code>)










