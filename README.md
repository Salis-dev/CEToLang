#CEToLang

A first attempt at a script to help convert cheat engine tables to c++, python or c#.

To Convert Cheat Engine Table:
-Run python Script
-Select your .CT Table
-Select Prefered Language
-Pick A Name And Save Output file


Script will go through ct files as xml, go through your cheatentries and read out the pointers use the module name to register a handle at the top (you need to adjust for whatever function or library you use to get a handle)
then declare a pointer and offsets to be used later by your program.

still very much a W.I.P
