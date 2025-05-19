Only German banks with FINTS access and PIN/TAN authentication
# Features
* Storing account statements, securities account data
 * Storing historical stock prices from Yahoo! Finance or AlphaVantage
 * Transfers and appointment transfers
 * Depot and historical price data evaluations
 * Transfer bank statements to Ledger application tables
# Free registrations
 * Request a free HBCI-ZKA registration key https://www.hbci-zka.de/
 * Request a free API key https://www.alphavantage.co/support/#support
# Installing on Windows
* Install MariaDB 10.5 and create an empty database >banken<
* Install Python 3.9
* Download GitHub project from https://github.com/WolfgangKramer/Banken-Ledger
The directory structure, should look like this:  
<pre>
bankarchive/  

|-- BANKEN
|	|-- src
|		|-- banking
|   			|-- __init__.py
|   			|-- bank.py
|			...
|   			|-- utils.py
|		|-- data
|			|-- background.gif
|			|-- Banking.py
</pre>
# Install Requirements
pip install -r requirements.txt  
# Create BAT file Banking.bat
> cd C:\BANKEN\src\data  
> py Banking.py
# Customizing
1. Customize Application INI File
2. Import Bankidentifier Data (Bankleitzahlendateien ungepackt) or use TableContent.zip
3. Import FINTS Server Data or use TableContent.zip
4. Create your Banks
# Tested Banks
 * BMW Bank (download of current daily transfer and savings transactions)
 * Consors 
 * Flatexdegiro Bank AG
 * VR Bank (not tested securities account data)
