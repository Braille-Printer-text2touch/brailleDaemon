# text2type Braille Protocol

The purpose of this protocol is to facilitate the communications of a printer, 
which might be given document information in a variety of formats, and the 
text2type braille printer. The braille printer operates on and recognizes a 
handful of control codes and ADA braille characters and contractions: ASCII text 
a-z (note, no capitals), the space, and 0-9.

Control codes are communicated to the printer by being on their own line and 
beginning with '@', which was chosen because ADA itself does not support a direct 
encoding for '@'. Other braille standards do, however, include support for '@', 
so '\@' is recognized as simply the character, not the start of a control code.

## List of Control Codes 

| Code | Function |
| -------------- | --------------- |
| @startdoc | Starts a new document (job) and instructs printer to treat all incoming text as the same job until @enddoc |
| @enddoc | Ends the current document (entire job) and instructs printer to eject the paper. |

