#!/usr/bin/env python

"""
Edit bulk MARC file according to RDA and local standards so that
it can go into the catalog with minimal manual intervention.
"""
import sys
import os
import argparse
from pymarc import marcxml, Field

def main(args=None):
    """Parse command line arguments.
    Iterate over MARCXML to process & write new file(s).
    """
    parser = argparse.ArgumentParser(
        description="""marc_process takes a MARCXML file exported from
        ArchivesSpace, does standard edits for upload to the catalog,
        and moves it to the shared drive.""")
    parser.add_argument(
        'files', nargs='*', help="one or more files to process")
    parser.add_argument(
        '--in-place', action='store_true', help="""use --in-place if
        you want to process the file where it is, instead of moving it
        to the standard shared drive location.""")
    parser.add_argument(
        '--keep-raw', action='store_true', help="""use --keep-raw if
        you want to keep the original file(s) downloaded from
        ArchivesSpace. Otherwise, they'll be deleted.""")

    # print help if no args given
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    if args is None:
        args = parser.parse_args()

    for i in range(len(args.files)):
        try:
            record = MarcRecord(args.files[i], args.in_place, args.keep_raw)
            record.process()
            record.write_out()
        except OSError:
            print("*ERROR*\nFile not found:", args.files[i])

class MarcRecord(object):
    """
    MARC record object represents a MARC record for a single archival collection.
    """
    def __init__(self, filename, in_place, keep_raw):
        self.xml_path = filename
        self.pymarc_record = None
        self.collection_number = None
        self.in_place = in_place
        self.keep_raw = keep_raw

    def process(self):
        """
        Read MARCXML to PyMARC object, edit according to RDA & local practices.
        Returns updated PyMARC record object
        """
        # MARCXML to pymarc record object
        record = marcxml.parse_xml_to_array(self.xml_path)[0]

        # update leader
        record.leader = '00000npcaa2200000Mi 4500'

        # 040: replace 'CURIV' with 'CRU' OCLC code in subfields a and c, append subfield e 'rda'
        for subfield in ['a', 'c']:
            record['040'][subfield] = 'CRU'
        record['040'].add_subfield('e', 'rda')

        # add 090 field with contents of 099 (099 will be deleted)
        record.add_field(
            Field(
                tag='090',
                indicators=record['099'].indicators,
                subfields=record['099'].subfields
                ))

        # 090 subfield a:
        # replace period with space in collection number, store collection #
        record['090']['a'] = record['090']['a'].replace('.', ' ')
        self.collection_number = record['090']['a']

        # 245
        # Add period to subfield A if missing
        if record['245']['a'].endswith('.') is False:
            record['245']['a'] = record['245']['a'] + '.'

        # remove date subfields from 245 & store dates in variables
        # (pymarc delete function returns value)
        inclusive_date = record['245'].delete_subfield('f')
        bulk_date = record['245'].delete_subfield('g')

        # format date value
        if inclusive_date is not None and bulk_date is not None:
            date = inclusive_date + ', bulk ' + bulk_date
        elif inclusive_date is None and bulk_date is not None:
            date = 'bulk ' + bulk_date
        elif inclusive_date is not None and bulk_date is None:
            date = inclusive_date
        if ' - ' in date:
            date = date.replace(' - ', '-')

        # add 264 (date)
        record.add_field(
            Field(
                tag='264',
                indicators=[' ', '0'],
                subfields=['c', date]
                ))

        # add 33x fields
        record.add_field(
            Field(
                tag='336',
                indicators=[' ', ' '],
                subfields=['a', 'unspecified',
                           '2', 'rdacontent']
                ))
        record.add_field(
            Field(
                tag='337',
                indicators=[' ', ' '],
                subfields=['a', 'unmediated',
                           '2', 'rdamedia']
                ))
        record.add_field(
            Field(
                tag='338',
                indicators=[' ', ' '],
                subfields=['a', 'unspecified',
                           '2', 'rdacarrier']
                ))

        #300a: lowercase 'Linear Feet'
        record['300']['a'] = record['300']['a'].replace('Linear Feet', 'linear feet')

        # update 856 language and subfield code (3 to g, "Finding aid online:" to "Finding aid:")
        record['856'].add_subfield('3', 'Finding aid:')
        record['856'].delete_subfield('z')
        record['856'].subfields = sorted(record['856'].subfields)

        # 600, 610, 650 & 651
        # Change second indicator '7' to '0', delete subfield 2
        for field in ['600', '610', '650', '651']:
            for instance in record.get_fields(field):
                if instance.indicators[1] == '7':
                    instance.indicators[1] = '0'
                instance.delete_subfield('2')

        # 630 indicator 1: number of nonfiling chars
        for field in record.get_fields('630'):
            # for now, just replace blank with zero to validate
            # TODO: add more sophisticated handling when I find a good test case
            if field.indicators[0] == ' ':
                field.indicators[0] = '0'

        # get and delete second 040
        record.remove_field(record.get_fields('040')[1])

        # get and delete 520 with first indicator 2
        for note in record.get_fields('520'):
            if note.indicators[0] == '2':
                record.remove_field(note)

        # delete other fields directly by tag
        record.remove_fields('049', '090', '555', '852')

        # sort fields in numeric order
        record.fields.sort(key=lambda x: x.tag)

        self.pymarc_record = record

    def write_out(self):
        """Write out processed file based on command-line options."""
        abs_path = os.path.abspath(self.xml_path)
        filename = self.collection_number.lower().replace(' ', '') + '.mrc'

        # set outpath
        if self.in_place is True:
            outdir = os.path.dirname(abs_path)
            outpath = os.path.join(outdir, filename)
        else:
            mts_share = "S:/Special Collections/Archives/Staff/Yoko Kudo/new/"
            outpath = os.path.join(mts_share, filename)

        # write out
        with open(outpath, 'wb') as outfile:
            outfile.write(self.pymarc_record.as_marc())

        # delete original exported file unless specified
        if self.keep_raw is True:
            pass
        elif self.in_place is True:
            pass
        else:
            os.remove(abs_path)

        # print confirmation
        print(filename, 'processed')
        print('Location:', outpath)
        sys.stdout.flush()
