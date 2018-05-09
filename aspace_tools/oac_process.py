#!/usr/bin/env python

import os
import codecs
import re
import sys
import argparse
import requests
from lxml import etree
from io import StringIO, BytesIO

def main(args=None):
    parser = argparse.ArgumentParser(
        description='oac_process takes an EAD file exported from ArchivesSpace, does standard edits for upload to OAC, and moves it to the appropriate location in the shared drive.')
    parser.add_argument(
        'files', nargs='*', help='one or more files to process')
    parser.add_argument(
        '--wrca', action='store_true', help='use --wrca if you are processing WRCA file(s). These are processed differently because the filenames and identifiers are nonstandard.')
    parser.add_argument(
        '--in-place', action='store_true', help='use --in-place if you want to process the file(s) in place (probably your Downloads folder) instead of moving it to the shared drive.')
    parser.add_argument(
        '--keep-raw', action='store_true', help='use --keep-raw if you want to keep the original file(s) downloaded from ArchivesSpace. Otherwise, it will be deleted.')
    
    #print help if no args given
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    if args is None:
        args = parser.parse_args()

    for i, value in enumerate(args.files):
        eadFile = args.files[i]
        processed = process(eadFile)
        newXML = processed[0]
        eadID = processed[1]

        #ead validation
        validate(newXML)

        #write out to file
        writeOut(eadFile, newXML, eadID, args.wrca, args.in_place, args.keep_raw)

def process(eadFile):
    parser = etree.XMLParser(resolve_entities=False, strip_cdata=False, remove_blank_text=True)
    xml = etree.parse(eadFile, parser)
    ns = '{urn:isbn:1-931666-22-9}'

    workingDir = os.path.dirname(os.path.abspath(__file__))
    stylesheet = 'stylesheets/aspace_oac.xslt'
    xslFile = os.path.join(workingDir,stylesheet)

    isodict = iso639()
                
    #apply xslt (does the majority of processing)
    xslt = etree.parse(xslFile)
    transform = etree.XSLT(xslt)
    newXML = transform(xml)

    #lxml processing for things i couldn't figure out how to catch in xslt
    #strip num tag from titleproper
    numtag = newXML.find('//{0}titleproper/{0}num'.format(ns))
    if numtag is not None:
        titleproper = numtag.getparent()
        titleproper.remove(numtag)
        titleproper.text = titleproper.text.strip()

    # ISO markup for <langmaterial> element
    # example: <langmaterial>The collection is in <language langcode="eng">English</language>
    langmat = newXML.find('//{0}archdesc/{0}did/{0}langmaterial'.format(ns))
    for langname in isodict.keys():
        try:
            if langname in langmat.text:
                langmarkup = '<language langcode="' + isodict.get(langname) + '"\>' +  langname + '</language>'
                langmat.text = langmat.text.replace(langname, langmarkup, 1)
        except TypeError: #this gets thrown when already has language element as child
            pass

    #get eadID to use as filename
    eadID = newXML.find('//{0}eadheader/{0}eadid'.format(ns)).text.strip()

    #to string for regex operations
    newXML = str(etree.tostring(newXML, pretty_print=True, xml_declaration=True, encoding='UTF-8'),'utf-8')

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

    return newXML, eadID

def iso639():
    isodict = {'Afar': 'aar', 'Abkhazian': 'abk', 'Achinese': 'ace', 'Acoli': 'ach', 'Adangme': 'ada', 'Adyghe; Adygei': 'ady', 'Afro-Asiatic languages': 'afa', 'Afrihili': 'afh', 'Afrikaans': 'afr', 'Ainu': 'ain', 'Akan': 'aka', 'Akkadian': 'akk', 'Albanian': 'alb', 'Aleut': 'ale', 'Algonquian languages': 'alg', 'Southern Altai': 'alt', 'Amharic': 'amh', 'English, Old (ca.450-1100)': 'ang', 'Angika': 'anp', 'Apache languages': 'apa', 'Arabic': 'ara', 'Official Aramaic (700-300 BCE); Imperial Aramaic (700-300 BCE)': 'arc', 'Aragonese': 'arg', 'Armenian': 'arm', 'Mapudungun; Mapuche': 'arn', 'Arapaho': 'arp', 'Artificial languages': 'art', 'Arawak': 'arw', 'Assamese': 'asm', 'Asturian; Bable; Leonese; Asturleonese': 'ast', 'Athapascan languages': 'ath', 'Australian languages': 'aus', 'Avaric': 'ava', 'Avestan': 'ave', 'Awadhi': 'awa', 'Aymara': 'aym', 'Azerbaijani': 'aze', 'Banda languages': 'bad', 'Bamileke languages': 'bai', 'Bashkir': 'bak', 'Baluchi': 'bal', 'Bambara': 'bam', 'Balinese': 'ban', 'Basque': 'baq', 'Basa': 'bas', 'Baltic languages': 'bat', 'Beja; Bedawiyet': 'bej', 'Belarusian': 'bel', 'Bemba': 'bem', 'Bengali': 'ben', 'Berber languages': 'ber', 'Bhojpuri': 'bho', 'Bihari languages': 'bih', 'Bikol': 'bik', 'Bini; Edo': 'bin', 'Bislama': 'bis', 'Siksika': 'bla', 'Bantu languages': 'bnt', 'Tibetan': 'tib', 'Bosnian': 'bos', 'Braj': 'bra', 'Breton': 'bre', 'Batak languages': 'btk', 'Buriat': 'bua', 'Buginese': 'bug', 'Bulgarian': 'bul', 'Burmese': 'bur', 'Blin; Bilin': 'byn', 'Caddo': 'cad', 'Central American Indian languages': 'cai', 'Galibi Carib': 'car', 'Catalan; Valencian': 'cat', 'Caucasian languages': 'cau', 'Cebuano': 'ceb', 'Celtic languages': 'cel', 'Czech': 'cze', 'Chamorro': 'cha', 'Chibcha': 'chb', 'Chechen': 'che', 'Chagatai': 'chg', 'Chinese': 'chi', 'Chuukese': 'chk', 'Mari': 'chm', 'Chinook jargon': 'chn', 'Choctaw': 'cho', 'Chipewyan; Dene Suline': 'chp', 'Cherokee': 'chr', 'Church Slavic; Old Slavonic; Church Slavonic; Old Bulgarian; Old Church Slavonic': 'chu', 'Chuvash': 'chv', 'Cheyenne': 'chy', 'Chamic languages': 'cmc', 'Montenegrin': 'cnr', 'Coptic': 'cop', 'Cornish': 'cor', 'Corsican': 'cos', 'Creoles and pidgins, English based': 'cpe', 'Creoles and pidgins, French-based': 'cpf', 'Creoles and pidgins, Portuguese-based': 'cpp', 'Cree': 'cre', 'Crimean Tatar; Crimean Turkish': 'crh', 'Creoles and pidgins': 'crp', 'Kashubian': 'csb', 'Cushitic languages': 'cus', 'Welsh': 'wel', 'Dakota': 'dak', 'Danish': 'dan', 'Dargwa': 'dar', 'Land Dayak languages': 'day', 'Delaware': 'del', 'Slave (Athapascan)': 'den', 'German': 'ger', 'Dogrib': 'dgr', 'Dinka': 'din', 'Divehi; Dhivehi; Maldivian': 'div', 'Dogri': 'doi', 'Dravidian languages': 'dra', 'Lower Sorbian': 'dsb', 'Duala': 'dua', 'Dutch, Middle (ca.1050-1350)': 'dum', 'Dutch; Flemish': 'dut', 'Dyula': 'dyu', 'Dzongkha': 'dzo', 'Efik': 'efi', 'Egyptian (Ancient)': 'egy', 'Ekajuk': 'eka', 'Greek, Modern (1453-)': 'gre', 'Elamite': 'elx', 'English': 'eng', 'English, Middle (1100-1500)': 'enm', 'Esperanto': 'epo', 'Estonian': 'est', 'Ewe': 'ewe', 'Ewondo': 'ewo', 'Fang': 'fan', 'Faroese': 'fao', 'Persian': 'per', 'Fanti': 'fat', 'Fijian': 'fij', 'Filipino; Pilipino': 'fil', 'Finnish': 'fin', 'Finno-Ugrian languages': 'fiu', 'Fon': 'fon', 'French': 'fre', 'French, Middle (ca.1400-1600)': 'frm', 'French, Old (842-ca.1400)': 'fro', 'Northern Frisian': 'frr', 'Eastern Frisian': 'frs', 'Western Frisian': 'fry', 'Fulah': 'ful', 'Friulian': 'fur', 'Ga': 'gaa', 'Gayo': 'gay', 'Gbaya': 'gba', 'Germanic languages': 'gem', 'Georgian': 'geo', 'Geez': 'gez', 'Gilbertese': 'gil', 'Gaelic; Scottish Gaelic': 'gla', 'Irish': 'gle', 'Galician': 'glg', 'Manx': 'glv', 'German, Middle High (ca.1050-1500)': 'gmh', 'German, Old High (ca.750-1050)': 'goh', 'Gondi': 'gon', 'Gorontalo': 'gor', 'Gothic': 'got', 'Grebo': 'grb', 'Greek, Ancient (to 1453)': 'grc', 'Guarani': 'grn', 'Swiss German; Alemannic; Alsatian': 'gsw', 'Gujarati': 'guj', "Gwich'in": 'gwi', 'Haida': 'hai', 'Haitian; Haitian Creole': 'hat', 'Hausa': 'hau', 'Hawaiian': 'haw', 'Hebrew': 'heb', 'Herero': 'her', 'Hiligaynon': 'hil', 'Himachali languages; Western Pahari languages': 'him', 'Hindi': 'hin', 'Hittite': 'hit', 'Hmong; Mong': 'hmn', 'Hiri Motu': 'hmo', 'Croatian': 'hrv', 'Upper Sorbian': 'hsb', 'Hungarian': 'hun', 'Hupa': 'hup', 'Iban': 'iba', 'Igbo': 'ibo', 'Icelandic': 'ice', 'Ido': 'ido', 'Sichuan Yi; Nuosu': 'iii', 'Ijo languages': 'ijo', 'Inuktitut': 'iku', 'Interlingue; Occidental': 'ile', 'Iloko': 'ilo', 'Interlingua (International Auxiliary Language Association)': 'ina', 'Indic languages': 'inc', 'Indonesian': 'ind', 'Indo-European languages': 'ine', 'Ingush': 'inh', 'Inupiaq': 'ipk', 'Iranian languages': 'ira', 'Iroquoian languages': 'iro', 'Italian': 'ita', 'Javanese': 'jav', 'Lojban': 'jbo', 'Japanese': 'jpn', 'Judeo-Persian': 'jpr', 'Judeo-Arabic': 'jrb', 'Kara-Kalpak': 'kaa', 'Kabyle': 'kab', 'Kachin; Jingpho': 'kac', 'Kalaallisut; Greenlandic': 'kal', 'Kamba': 'kam', 'Kannada': 'kan', 'Karen languages': 'kar', 'Kashmiri': 'kas', 'Kanuri': 'kau', 'Kawi': 'kaw', 'Kazakh': 'kaz', 'Kabardian': 'kbd', 'Khasi': 'kha', 'Khoisan languages': 'khi', 'Central Khmer': 'khm', 'Khotanese; Sakan': 'kho', 'Kikuyu; Gikuyu': 'kik', 'Kinyarwanda': 'kin', 'Kirghiz; Kyrgyz': 'kir', 'Kimbundu': 'kmb', 'Konkani': 'kok', 'Komi': 'kom', 'Kongo': 'kon', 'Korean': 'kor', 'Kosraean': 'kos', 'Kpelle': 'kpe', 'Karachay-Balkar': 'krc', 'Karelian': 'krl', 'Kru languages': 'kro', 'Kurukh': 'kru', 'Kuanyama; Kwanyama': 'kua', 'Kumyk': 'kum', 'Kurdish': 'kur', 'Kutenai': 'kut', 'Ladino': 'lad', 'Lahnda': 'lah', 'Lamba': 'lam', 'Lao': 'lao', 'Latin': 'lat', 'Latvian': 'lav', 'Lezghian': 'lez', 'Limburgan; Limburger; Limburgish': 'lim', 'Lingala': 'lin', 'Lithuanian': 'lit', 'Mongo': 'lol', 'Lozi': 'loz', 'Luxembourgish; Letzeburgesch': 'ltz', 'Luba-Lulua': 'lua', 'Luba-Katanga': 'lub', 'Ganda': 'lug', 'Luiseno': 'lui', 'Lunda': 'lun', 'Luo (Kenya and Tanzania)': 'luo', 'Lushai': 'lus', 'Macedonian': 'mac', 'Madurese': 'mad', 'Magahi': 'mag', 'Marshallese': 'mah', 'Maithili': 'mai', 'Makasar': 'mak', 'Malayalam': 'mal', 'Mandingo': 'man', 'Maori': 'mao', 'Austronesian languages': 'map', 'Marathi': 'mar', 'Masai': 'mas', 'Malay': 'may', 'Moksha': 'mdf', 'Mandar': 'mdr', 'Mende': 'men', 'Irish, Middle (900-1200)': 'mga', "Mi'kmaq; Micmac": 'mic', 'Minangkabau': 'min', 'Uncoded languages': 'mis', 'Mon-Khmer languages': 'mkh', 'Malagasy': 'mlg', 'Maltese': 'mlt', 'Manchu': 'mnc', 'Manipuri': 'mni', 'Manobo languages': 'mno', 'Mohawk': 'moh', 'Mongolian': 'mon', 'Mossi': 'mos', 'Multiple languages': 'mul', 'Munda languages': 'mun', 'Creek': 'mus', 'Mirandese': 'mwl', 'Marwari': 'mwr', 'Mayan languages': 'myn', 'Erzya': 'myv', 'Nahuatl languages': 'nah', 'North American Indian languages': 'nai', 'Neapolitan': 'nap', 'Nauru': 'nau', 'Navajo; Navaho': 'nav', 'Ndebele, South; South Ndebele': 'nbl', 'Ndebele, North; North Ndebele': 'nde', 'Ndonga': 'ndo', 'Low German; Low Saxon; German, Low; Saxon, Low': 'nds', 'Nepali': 'nep', 'Nepal Bhasa; Newari': 'new', 'Nias': 'nia', 'Niger-Kordofanian languages': 'nic', 'Niuean': 'niu', 'Norwegian Nynorsk; Nynorsk, Norwegian': 'nno', 'Bokmål, Norwegian; Norwegian Bokmål': 'nob', 'Nogai': 'nog', 'Norse, Old': 'non', 'Norwegian': 'nor', "N'Ko": 'nqo', 'Pedi; Sepedi; Northern Sotho': 'nso', 'Nubian languages': 'nub', 'Classical Newari; Old Newari; Classical Nepal Bhasa': 'nwc', 'Chichewa; Chewa; Nyanja': 'nya', 'Nyamwezi': 'nym', 'Nyankole': 'nyn', 'Nyoro': 'nyo', 'Nzima': 'nzi', 'Occitan (post 1500)': 'oci', 'Ojibwa': 'oji', 'Oriya': 'ori', 'Oromo': 'orm', 'Osage': 'osa', 'Ossetian; Ossetic': 'oss', 'Turkish, Ottoman (1500-1928)': 'ota', 'Otomian languages': 'oto', 'Papuan languages': 'paa', 'Pangasinan': 'pag', 'Pahlavi': 'pal', 'Pampanga; Kapampangan': 'pam', 'Panjabi; Punjabi': 'pan', 'Papiamento': 'pap', 'Palauan': 'pau', 'Persian, Old (ca.600-400 B.C.)': 'peo', 'Philippine languages': 'phi', 'Phoenician': 'phn', 'Pali': 'pli', 'Polish': 'pol', 'Pohnpeian': 'pon', 'Portuguese': 'por', 'Prakrit languages': 'pra', 'Provençal, Old (to 1500);Occitan, Old (to 1500)': 'pro', 'Pushto; Pashto': 'pus', 'Reserved for local use': 'qaa-qtz', 'Quechua': 'que', 'Rajasthani': 'raj', 'Rapanui': 'rap', 'Rarotongan; Cook Islands Maori': 'rar', 'Romance languages': 'roa', 'Romansh': 'roh', 'Romany': 'rom', 'Romanian; Moldavian; Moldovan': 'rum', 'Rundi': 'run', 'Aromanian; Arumanian; Macedo-Romanian': 'rup', 'Russian': 'rus', 'Sandawe': 'sad', 'Sango': 'sag', 'Yakut': 'sah', 'South American Indian languages': 'sai', 'Salishan languages': 'sal', 'Samaritan Aramaic': 'sam', 'Sanskrit': 'san', 'Sasak': 'sas', 'Santali': 'sat', 'Sicilian': 'scn', 'Scots': 'sco', 'Selkup': 'sel', 'Semitic languages': 'sem', 'Irish, Old (to 900)': 'sga', 'Sign Languages': 'sgn', 'Shan': 'shn', 'Sidamo': 'sid', 'Sinhala; Sinhalese': 'sin', 'Siouan languages': 'sio', 'Sino-Tibetan languages': 'sit', 'Slavic languages': 'sla', 'Slovak': 'slo', 'Slovenian': 'slv', 'Southern Sami': 'sma', 'Northern Sami': 'sme', 'Sami languages': 'smi', 'Lule Sami': 'smj', 'Inari Sami': 'smn', 'Samoan': 'smo', 'Skolt Sami': 'sms', 'Shona': 'sna', 'Sindhi': 'snd', 'Soninke': 'snk', 'Sogdian': 'sog', 'Somali': 'som', 'Songhai languages': 'son', 'Sotho, Southern': 'sot', 'Spanish': 'spa', 'Sardinian': 'srd', 'Sranan Tongo': 'srn', 'Serbian': 'srp', 'Serer': 'srr', 'Nilo-Saharan languages': 'ssa', 'Swati': 'ssw', 'Sukuma': 'suk', 'Sundanese': 'sun', 'Susu': 'sus', 'Sumerian': 'sux', 'Swahili': 'swa', 'Swedish': 'swe', 'Classical Syriac': 'syc', 'Syriac': 'syr', 'Tahitian': 'tah', 'Tai languages': 'tai', 'Tamil': 'tam', 'Tatar': 'tat', 'Telugu': 'tel', 'Timne': 'tem', 'Tereno': 'ter', 'Tetum': 'tet', 'Tajik': 'tgk', 'Tagalog': 'tgl', 'Thai': 'tha', 'Tigre': 'tig', 'Tigrinya': 'tir', 'Tiv': 'tiv', 'Tokelau': 'tkl', 'Klingon; tlhIngan-Hol': 'tlh', 'Tlingit': 'tli', 'Tamashek': 'tmh', 'Tonga (Nyasa)': 'tog', 'Tonga (Tonga Islands)': 'ton', 'Tok Pisin': 'tpi', 'Tsimshian': 'tsi', 'Tswana': 'tsn', 'Tsonga': 'tso', 'Turkmen': 'tuk', 'Tumbuka': 'tum', 'Tupi languages': 'tup', 'Turkish': 'tur', 'Altaic languages': 'tut', 'Tuvalu': 'tvl', 'Twi': 'twi', 'Tuvinian': 'tyv', 'Udmurt': 'udm', 'Ugaritic': 'uga', 'Uighur; Uyghur': 'uig', 'Ukrainian': 'ukr', 'Umbundu': 'umb', 'Undetermined': 'und', 'Urdu': 'urd', 'Uzbek': 'uzb', 'Vai': 'vai', 'Venda': 'ven', 'Vietnamese': 'vie', 'Volapük': 'vol', 'Votic': 'vot', 'Wakashan languages': 'wak', 'Wolaitta; Wolaytta': 'wal', 'Waray': 'war', 'Washo': 'was', 'Sorbian languages': 'wen', 'Walloon': 'wln', 'Wolof': 'wol', 'Kalmyk; Oirat': 'xal', 'Xhosa': 'xho', 'Yao': 'yao', 'Yapese': 'yap', 'Yiddish': 'yid', 'Yoruba': 'yor', 'Yupik languages': 'ypk', 'Zapotec': 'zap', 'Blissymbols; Blissymbolics; Bliss': 'zbl', 'Zenaga': 'zen', 'Standard Moroccan Tamazight': 'zgh', 'Zhuang; Chuang': 'zha', 'Zande languages': 'znd', 'Zulu': 'zul', 'Zuni': 'zun', 'No linguistic content; Not applicable': 'zxx', 'Zaza; Dimili; Dimli; Kirdki; Kirmanjki; Zazaki': 'zza'}
    return isodict

def validate(xmlString):
    #validate against schema
    #parse string back into lxml
    checkdoc = bytes(xmlString,'utf-8')
    checkdoc = etree.parse(BytesIO(checkdoc))
    #grab schema from Library of Congress website
    loc = requests.get('https://www.loc.gov/ead/ead.xsd').text
    f = BytesIO(bytes(loc,'utf-8'))
    xmlschema_doc = etree.parse(f)
    xmlschema = etree.XMLSchema(xmlschema_doc)
    #evaluate and print validation status
    if xmlschema.validate(checkdoc) == False:
        print('WARNING: EAD validation failed. Check file for errors.')
    else:
        print('EAD validated')

def writeOut(eadPath, newXML, eadID, isWRCA, inPlace, keepRaw):
    filename = os.path.basename(eadPath)
    absolutePath = os.path.abspath(eadPath)

    #normalize filename if it matches ArchivesSpace automated naming scheme
    aspaceFileRE = re.compile(r'([A-Za-z0-9\.]+)_[0-9]{8}_[0-9]{6}_UTC__ead\.xml')    
    autonamed = aspaceFileRE.match(filename)
    if autonamed is not None:
        filename = eadID
    #leave other filenames alone
    else:
        pass

    #set outpath
    if inPlace == True:
        outdir = os.path.dirname(absolutePath)
        outpath = os.path.join(outdir,filename)
    else:
        #choose directory
        eadHome = "S:/Special Collections/Archives/Collections/"
        if filename.startswith('wr'):
            isWRCA = True
        if isWRCA == True:
            subdir = 'WRCA/WRCA_EAD/'
        elif filename.startswith('ms'):
            subdir = 'MS/MS_EAD/'
        elif filename.startswith('ua'):
            subdir = 'UA/UA_EAD/'
        outpath = os.path.join(eadHome,subdir,filename)

    #write out
    with codecs.open(outpath, 'w', 'utf-8') as outfile:
        outfile.write(newXML)

    #delete original exported file unless specified
    if keepRaw == True:
        pass
    else:
        os.remove(absolutePath)

    #print confirmation
    print(filename,'processed')
    print('Location:',outpath)
    sys.stdout.flush()

# main() idiom
if __name__ == "__main__":
    sys.exit(main())