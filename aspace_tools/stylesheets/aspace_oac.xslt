<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:ead="urn:isbn:1-931666-22-9"
    xmlns="urn:isbn:1-931666-22-9">
    <xsl:output method="xml" encoding="UTF-8"/>
    <!--identity template-->
    <xsl:template match="@*|node()">
        <xsl:copy>
            <xsl:apply-templates select="@*|node()"/>
        </xsl:copy>
    </xsl:template>
    <!--order titles-->
    <xsl:template match="ead:titlestmt">
        <titlestmt>
            <xsl:copy-of select="ead:titleproper[not(@type)]"/>
            <xsl:copy-of select="ead:titleproper[@type='filing']"/>
            <xsl:copy-of select="ead:author"/>
        </titlestmt>
    </xsl:template>
    <!-- change publication statement -->
    <xsl:template match="ead:publicationstmt">
        <publicationstmt>
            <publisher>Special Collections &amp; University Archives</publisher>
            <address>
            <addressline>The UCR Library</addressline>
            <addressline>P.O. Box 5900</addressline>
            <addressline>University of California</addressline>
            <addressline>Riverside, California 92517-5900</addressline>
            <addressline>Phone: 951-827-3233</addressline>
            <addressline>Fax: 951-827-4673</addressline>
            <addressline>Email: specialcollections@ucr.edu</addressline>
            <addressline>URL: http://library.ucr.edu/libraries/special-collections-university-archives</addressline>
        </address>
            <date>&#x00A9; <xsl:copy-of select="ead:p/ead:date[1]/node()"/></date>
            <p>The Regents of the University of California. All rights reserved.</p>
        </publicationstmt>
    </xsl:template>
    <!-- change langusage element -->
    <xsl:template match="ead:profiledesc/ead:langusage">
        <langusage>Description is in <language langcode="eng" scriptcode="Latn"
            >English</language></langusage>
    </xsl:template>
    <!--DID stuff-->
    <xsl:template match="ead:archdesc/ead:did[1]">
        <did>
            <head>Descriptive Summary</head>
            <unittitle label="Title">
                <xsl:copy-of select="ead:unittitle/node()"/>
            </unittitle>
            <xsl:for-each select="ead:unitdate">
                <xsl:copy-of select="."/>
            </xsl:for-each>
            <unitid label="Collection Number" repositorycode="US-CURIV" countrycode="US">
                <!--translate function replaces character: this replaces period with space in collection number-->
                <xsl:value-of select="translate(ead:unitid,'.',' ')"/>
            </unitid>
            <xsl:for-each select="ead:origination">
                <xsl:choose>
                    <xsl:when test="@label='creator' or @label='Creator'">
                        <origination label="Creator">
                            <xsl:copy-of select="child::node()"/>
                        </origination>
                    </xsl:when>
                    <xsl:when test="@label='source'">
                        <origination label="Source">
                            <xsl:copy-of select="child::node()"/>
                        </origination>
                    </xsl:when>
                </xsl:choose>
            </xsl:for-each>
            <xsl:for-each select="ead:physdesc">
                <physdesc label="Extent">
                    <xsl:copy-of select="child::node()"/>
                </physdesc>
            </xsl:for-each>
            <repository label="Repository">
                <corpname source="lcnaf">Rivera Library. Special Collections Department.</corpname>
                <address>
          <addressline>Riverside, CA 92517-5900</addressline>
          </address>
            </repository>
            <xsl:copy-of select="ead:abstract"/>
            <!--haven't figured out how to add <language> tag and ISO value-->
            <langmaterial label="Languages">
                <xsl:value-of select="ead:langmaterial"/>
            </langmaterial>
        </did>
    </xsl:template>
    <!--add controlaccess head and description-->
    <xsl:template match="ead:controlaccess">
        <controlaccess>
            <head>Indexing Terms</head>
            <p>The following terms have been used to index the description of this collection in the
                library's online public access catalog.</p>
            <xsl:if test="ead:famname|ead:persname|ead:corpname|ead:subject|ead:geogname">
                <controlaccess>
                    <head>Subjects</head>
                    <xsl:for-each select="ead:famname|ead:persname|ead:corpname">
                        <xsl:apply-templates select="."/>
                    </xsl:for-each>
                    <xsl:for-each select="ead:subject|ead:geogname">
                        <xsl:apply-templates select="."/>
                    </xsl:for-each>
                </controlaccess>
            </xsl:if>
            <xsl:if test="ead:genreform">
                <controlaccess>
                    <head>Genres and Forms of Materials</head>
                    <xsl:apply-templates select="ead:genreform"/>
                </controlaccess>
            </xsl:if>
        </controlaccess>
    </xsl:template>
    <!--remove duplicate name values-->
    <xsl:template match="ead:persname[.=preceding-sibling::ead:persname]"/>
    <xsl:template match="ead:corpname[.=preceding-sibling::ead:corpname]"/>
    <xsl:template match="ead:famname[.=preceding-sibling::ead:famname]"/>
    <!--trying a different approach to just remove empty tags (so preserves dsc if not empty-->
    <xsl:template match="*[not(@*|*|comment()|processing-instruction())          and
        normalize-space()=''         ]"/>
    <!--unitid comes before unittitle in DID at series level-->
    <xsl:template match="//*[@level='series']/ead:did">
        <did>
            <xsl:copy-of select="ead:unitid"/>
            <xsl:copy-of select="ead:unittitle"/>
            <xsl:copy-of select="ead:unitdate"/>
        </did>
    </xsl:template>
</xsl:stylesheet>
