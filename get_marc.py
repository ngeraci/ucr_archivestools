#!/usr/bin/env python

import sys
import argparse
import requests
import json
import secrets
import codecs
import re
import csv
from lxml import etree
from lxml.builder import E
import pymarc

def main(args=None):
    parser = argparse.ArgumentParser(
        description='get_marc takes an EAD finding aid and fetches and processes the corresponding MARC record from ArchivesSpace')
    parser.add_argument(
        'file', nargs=1, help='file to process')
    if args is None:
        args = parser.parse_args()

    export_marc(args.file[0])

def export_marc(eadID):
	#get login info in secrets.py file
    baseURL = secrets.baseURL
    user = secrets.user
    password = secrets.password
    #authenticate
    auth = requests.post(baseURL + '/users/'+ user +'/login?password='+password).json()
    session = auth["session"]
    headers = {'X-ArchivesSpace-Session':session}

    #loop thru resources
    for repo in [3,4,5]:
        repo = str(repo)
        ids = requests.get(baseURL + '/repositories/' + repo + '/resources?all_ids=true', headers=headers)
        for i in ids.json():
        	try:
	            resource = requests.get(baseURL + '/repositories/' + repo + '/resources/' + str(i), headers=headers).json()
	            if resource['ead_id'] == eadID:
	                marcXML = requests.get(baseURL + '/repositories/'+ repo +'/resources/marc21/'+str(i)+'.xml', headers=headers)
	                break
	        except KeyError:
	        	pass

    record = marcXML.text
    process_marc(record, eadID)

def process_marc(marcxml, ead_id):

    #replace period with space in collection numbers, needed for OAC URL retrieval
    matchCollNumber = re.compile(r'(MS|UA|WRCA)\.([0-9]{3})')
    marcxml = matchCollNumber.sub(r'\1 \2',marcxml)
    matchAltCollNumber = re.compile(r'(WR)\.([0-9]{2})\.([0-9]{2})')
    marcxml = matchAltCollNumber.sub(r'\1 \2 \3',marcxml)

    #remove xml declaration due to lxml string processing quirk
    marcxml = marcxml.replace('<?xml version="1.0" encoding="UTF-8"?>','')

    #get OAC urls in dict from CSV export
    with open('ms_oac.csv', mode='r') as infile:
        reader = csv.reader(infile)
        urlDict = {rows[1]:rows[0] for rows in reader}   

    #lxml processing
    root = etree.XML(marcxml)
    record = root.xpath("/document/*[namespace-uri()='http://www.loc.gov/MARC21/slim' and local-name()='collection']/*[namespace-uri()='http://www.loc.gov/MARC21/slim' and local-name()='record']")
    #loop through datafield tags
    for field in record.getchildren():
        #update leader
        if field.tag == '{http://www.loc.gov/MARC21/slim}leader':
            field.text = '00000npcaa2200000Ic 4500'
        elif field.tag == "{http://www.loc.gov/MARC21/slim}datafield":
            fieldNumber = field.attrib['tag']
            #store collection number in variable, then remove 852
            if fieldNumber == '852':
                subfield = field.getchildren()
                collNumber = subfield[2].text
                field.getparent().remove(field)
            elif fieldNumber == '040':
                #replace 'CURIV' with 'CRU' OCLC code
                subfield = field.getchildren()
                for s in subfield:
                    s.text = s.text.replace('CURIV','CRU')
                #append subfield e 'rda'
                field.append(E('subfield','rda',code='e'))
            #delete dates from 245 and store in variable
            elif fieldNumber == '245':
                #initialize variables
                inclusiveDate = None
                bulkDate = None
                #get subfields
                subfield = field.getchildren()
                for s in subfield:
                    if s.attrib['code'] == 'a':
                        if s.text.endswith('.') == False:
                            s.text += '.'
                    elif s.attrib['code'] == 'f':
                        inclusiveDate = s.text
                        #if 245 has “undated” in $f, delete it, and add “circa” to the date
                        if ', undated' in inclusiveDate:
                            inclusiveDate = 'circa ' + inclusiveDate.replace(', undated','')
                        s.getparent().remove(s)
                    #subfield g (bulk date) - get value
                    elif s.attrib['code'] == 'g':
                        bulkDate = s.text
                        s.getparent().remove(s)
                    #format date value
                    if inclusiveDate is not None and bulkDate is not None:
                        date = inclusiveDate + ', bulk ' + bulkDate
                    elif inclusiveDate is None and bulkDate is not None:
                        date = 'bulk ' + bulkDate
                    elif inclusiveDate is not None and bulkDate is None:
                        date = inclusiveDate
                    else:
                        continue
                    if ' - ' in date:
                        date = date.replace(' - ','-')
                    if date.endswith('.') == False:
                        date += '.'
               #add 264 following 245
                record.insert(record.index(field)+1,
                    E('datafield',
                        E('subfield',date,code='c'),
                        #tagToReplace because having an attribute named 'tag' was throwing an error in this function
                        ind1='',ind2='0',tagToReplace='264'))
            #append additional 3xx fields following 300
            elif fieldNumber == '300':
                record.insert(record.index(field)+1,
                    E('datafield',
                        E('subfield','unspecified',code='a'),
                        E('subfield','rdacontent',code='2'),
                        #tagToReplace because having an attribute named 'tag' was throwing an error in this function
                        ind1='',ind2='',tagToReplace='336'))
                record.insert(record.index(field)+2,
                    E('datafield',
                        E('subfield','unmediated',code='a'),
                        E('subfield','rdamedia', code='2'),
                        #tagToReplace because having an attribute named 'tag' was throwing an error in this function
                        ind1='',ind2='',tagToReplace='337'))
                record.insert(record.index(field)+2,
                    E('datafield',
                        E('subfield','unspecified',code='a'),
                        E('subfield','rdacarrier',code='2'),
                        #tagToReplace because having an attribute named 'tag' was throwing an error in this function
                        ind1='',ind2='',tagToReplace='338'))
            #delete 520 for scopecontent
            elif fieldNumber == '520' and field.attrib['ind1'] == '2':
                field.getparent().remove(field)
            #change field 534 to 524
            elif fieldNumber == '534':
                fieldNumber = '524'
            #remove 555 field
            elif fieldNumber == '555':
                field.getparent().remove(field)
            #600, 610, 650 & 651 fields with second indicator '7' should be changed to second indicator '0', and delete subfield 2
            elif fieldNumber in ['600','610','650','651']:
                field.attrib['ind2'] = '0'
                subfield = field.getchildren()
                subfieldCodes = []
                for s in subfield:
                    subfieldCodes.append(s.attrib['code'])
                for s in subfield:
                    if s.attrib['code'] == '2':
                        s.getparent().remove(s)
                    elif s.attrib['code'] == 'a':
                        if 'z' in subfieldCodes or 'x' in subfieldCodes:
                            pass
                        elif 'd' in subfieldCodes:
                            s.text += ','                           
                        else:
                            s.text += '.'
                    elif s.attrib['code'] == 'x':
                        #add a period only if it's the last value - in progress
                        valueIndex = subfieldCodes.index(s.attrib['code'])
                        maxIndex = max(loc for loc, val in enumerate(subfieldCodes) if val == 'x')
                        if 'z' not in subfieldCodes:
                            if valueIndex == maxIndex:
                                s.text += '.'
                    elif s.attrib['code'] == 'z':
                        s.text += '.'

            #655 period
            elif fieldNumber == '655':
                subfield = field.getchildren()
                for s in subfield:
                    if s.attrib['code'] == 'a':
                        if s.text.endswith('.') == False:
                            s.text += '.'
            #100, 110, 700, 710 punctuation
            elif fieldNumber in ['100','110','700','710']:
                subfield = field.getchildren()
                subfieldCodes = []
                for s in subfield:
                    subfieldCodes.append(s.attrib['code'])
                for s in subfield:
                    if s.attrib['code'] == 'a':
                        #if subfield b exists and A doesn't already have a period, add period
                        if 'b' in subfieldCodes and s.text.endswith('.') == False:
                            s.text += '.'
                        elif 'd' in subfieldCodes:
                            s.text += ','
                        #if there's E but no B or D, and A doesn't end with a hyphen, append comma 
                        elif 'e' in subfieldCodes and s.text.endswith('-') == False:
                            s.text += ','
                    elif s.attrib['code'] == 'b':
                        if 'e' in subfieldCodes:
                            s.text += ','
                    elif s.attrib['code'] == 'd':
                        if 'e' in subfieldCodes:
                            s.text += ','
                        else:
                            s.text += '.'
                    elif s.attrib['code'] == 'e':
                        s.text += '.'
            #856
            elif fieldNumber == '856':
                #add subfield u (URL)
                field.append(etree.Element('subfield', code='u'))
                #get subfields
                subfield = field.getchildren()
                #update subfield 3 (text that precedes URL)
                subfield[0].attrib['code'] = '3'
                subfield[0].text = 'Finding aid:'
                #add URL to subfield U
                try:
                    subfield[1].text = urlDict[collNumber]
                except:
                    # print(collNumber + ' URL not found')
                    pass

    #write to string        
    marcxml = etree.tostring(root, encoding='unicode')
    #miscellaneous text processing
    #address spacing issues caused by ead markup like <emph>
    doubleSpace = re.compile(r'(\S)  (\S)')
    marcxml = doubleSpace.sub(r'\1 \2',marcxml)
    punctWithSpace = re.compile(r' (\.|,|:)')
    marcxml = punctWithSpace.sub(r'\1',marcxml)
    marcxml = marcxml.replace('> ','>')
    #change double paren in 300 field to single
    marcxml = marcxml.replace('((','(')
    marcxml = marcxml.replace('))',')')
    #lowercase 'Linear Feet'
    marcxml = marcxml.replace('Linear Feet','linear feet')
    #replace tagToReplace with tag
    marcxml = marcxml.replace('tagToReplace','tag')
    #xml declaration
    marcxml = '<?xml version="1.0" encoding="UTF-8"?>' + marcxml
 
    #write out to file
    outpath = ead_id[:-3] + '.mrc'
    with codecs.open(outpath, 'w', 'utf-8') as f:
        f.write(marcxml)

# main() idiom
if __name__ == "__main__":
    sys.exit(main())