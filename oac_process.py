#!/usr/bin/env python

import os
import codecs
import re
import sys
from lxml import etree
from iso639b_dict import iso639

def process():
    basedir = 'C:\\Users\\ngeraci\\Documents\\ead_export\\'
    repos = ['MS','UA','WRCA']
    parser = etree.XMLParser(resolve_entities=False, strip_cdata=False, remove_blank_text=True)
    xslFilename = 'stylesheets/aspace_oac.xslt'
    isodict = iso639()

    #loop through each repository's local directory for xml files
    for repo in repos:
        directory = os.fsencode(os.path.join(basedir,'raw_export\\',repo))
        for file in os.listdir(directory):
            filename = os.fsdecode(file)
            if filename.endswith('.xml'):
                xml = etree.parse(os.fsencode(os.path.join(directory,file)))
                
                #apply xslt (does the majority of processing)
                xslt = etree.parse(xslFilename)
                transform = etree.XSLT(xslt)
                newXML = transform(xml)

                #processing for things i couldn't figure out how to catch in xslt
                for element in newXML.iter():
                    #strip num tag from titleproper
                    if element.tag == '{urn:isbn:1-931666-22-9}titleproper':
                        for child in element.getchildren():
                            if child.tag == '{urn:isbn:1-931666-22-9}num':
                                element.remove(child)
                                element.text = element.text.strip()
                    #ISO markup for <langmaterial> element
                    #example: <langmaterial>The collection is in <language langcode="eng">English</language>
                    elif element.tag == '{urn:isbn:1-931666-22-9}langmaterial':
                        for langname in isodict.keys():
                            try:
                                if langname in element.text:
                                    langmarkup = '<language langcode="' + isodict.get(langname) + '"\>' +  langname + '</language>'
                                    element.text = element.text.replace(langname, langmarkup, 1)
                            except:
                                pass
                                #it would be good to have better error handling here


                #to string for regex operations
                newXML = str(newXML)
                ##remove the namespace declarations within elements
                newXML = re.sub(r'xmlns:xs="http:\/\/www\.w3\.org\/2001\/XMLSchema"\s+xmlns:ead="urn:isbn:1-931666-22-9"','',newXML)
                #lowercase "linear feet"
                newXML = re.sub(r'Linear\s+Feet','linear feet',newXML)

                #hacky angle bracket stuff for langmaterial
                #want to figure out how to do the markup more elegantly w/ lxml, should eliminate need for this
                newXML = newXML.replace('&lt;/','</')
                newXML = newXML.replace('&lt;','<')
                newXML = newXML.replace('\&gt;','>')
                newXML = newXML.replace('&gt;','>')

                #write out to new file
                outpath = os.fsencode(os.path.join(basedir,'processed\\',repo,filename))
                f = codecs.open(outpath, 'w', 'utf-8')
                f.write(newXML)
                f.close()

                #print confirmation
                print(filename,' processed to ',outpath)
                sys.stdout.flush()

process()