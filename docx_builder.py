"""
Script to generate the complete, comprehensive, professional University Documentation
for the Office Management System (OMS) as a native Microsoft Word (.docx) file.
"""

import os
import zipfile
import html

def escape(text):
    return html.escape(str(text))

class DocxBuilder:
    def __init__(self):
        self.body_elements = []

    def add_title(self, text):
        xml = f"""
        <w:p>
            <w:pPr>
                <w:jc w:val="center"/>
                <w:spacing w:before="480" w:after="160"/>
            </w:pPr>
            <w:r>
                <w:rPr>
                    <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>
                    <w:b/>
                    <w:sz w:val="56"/>
                    <w:color w:val="1E3A8A"/>
                </w:rPr>
                <w:t>{escape(text)}</w:t>
            </w:r>
        </w:p>
        """
        self.body_elements.append(xml)

    def add_subtitle(self, text):
        xml = f"""
        <w:p>
            <w:pPr>
                <w:jc w:val="center"/>
                <w:spacing w:before="0" w:after="360"/>
            </w:pPr>
            <w:r>
                <w:rPr>
                    <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>
                    <w:i/>
                    <w:sz w:val="28"/>
                    <w:color w:val="475569"/>
                </w:rPr>
                <w:t>{escape(text)}</w:t>
            </w:r>
        </w:p>
        """
        self.body_elements.append(xml)

    def add_heading1(self, text):
        xml = f"""
        <w:p>
            <w:pPr>
                <w:spacing w:before="400" w:after="160"/>
                <w:pBdr>
                    <w:bottom w:val="single" w:sz="12" w:space="4" w:color="1E3A8A"/>
                </w:pBdr>
            </w:pPr>
            <w:r>
                <w:rPr>
                    <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>
                    <w:b/>
                    <w:sz w:val="36"/>
                    <w:color w:val="1E3A8A"/>
                </w:rPr>
                <w:t>{escape(text)}</w:t>
            </w:r>
        </w:p>
        """
        self.body_elements.append(xml)

    def add_heading2(self, text):
        xml = f"""
        <w:p>
            <w:pPr>
                <w:spacing w:before="280" w:after="120"/>
            </w:pPr>
            <w:r>
                <w:rPr>
                    <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>
                    <w:b/>
                    <w:sz w:val="28"/>
                    <w:color w:val="0F172A"/>
                </w:rPr>
                <w:t>{escape(text)}</w:t>
            </w:r>
        </w:p>
        """
        self.body_elements.append(xml)

    def add_heading3(self, text):
        xml = f"""
        <w:p>
            <w:pPr>
                <w:spacing w:before="200" w:after="80"/>
            </w:pPr>
            <w:r>
                <w:rPr>
                    <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>
                    <w:b/>
                    <w:sz w:val="24"/>
                    <w:color w:val="2563EB"/>
                </w:rPr>
                <w:t>{escape(text)}</w:t>
            </w:r>
        </w:p>
        """
        self.body_elements.append(xml)

    def add_paragraph(self, text, bold_prefix=None, italic=False, color="1E293B", align="both"):
        runs_xml = ""
        if bold_prefix:
            runs_xml += f"""
            <w:r>
                <w:rPr>
                    <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>
                    <w:b/>
                    <w:sz w:val="22"/>
                    <w:color w:val="0F172A"/>
                </w:rPr>
                <w:t xml:space="preserve">{escape(bold_prefix)} </w:t>
            </w:r>
            """
        italic_xml = "<w:i/>" if italic else ""
        runs_xml += f"""
        <w:r>
            <w:rPr>
                <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>
                {italic_xml}
                <w:sz w:val="22"/>
                <w:color w:val="{color}"/>
            </w:rPr>
            <w:t xml:space="preserve">{escape(text)}</w:t>
        </w:r>
        """
        xml = f"""
        <w:p>
            <w:pPr>
                <w:jc w:val="{align}"/>
                <w:spacing w:before="60" w:after="120" w:line="276" w:lineRule="auto"/>
            </w:pPr>
            {runs_xml}
        </w:p>
        """
        self.body_elements.append(xml)

    def add_bullet(self, text, bold_title=None):
        runs_xml = ""
        if bold_title:
            runs_xml += f"""
            <w:r>
                <w:rPr>
                    <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>
                    <w:b/>
                    <w:sz w:val="22"/>
                    <w:color w:val="0F172A"/>
                </w:rPr>
                <w:t xml:space="preserve">{escape(bold_title)}: </w:t>
            </w:r>
            """
        runs_xml += f"""
        <w:r>
            <w:rPr>
                <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>
                <w:sz w:val="22"/>
                <w:color w:val="334155"/>
            </w:rPr>
            <w:t xml:space="preserve">{escape(text)}</w:t>
        </w:r>
        """
        xml = f"""
        <w:p>
            <w:pPr>
                <w:pStyle w:val="ListParagraph"/>
                <w:spacing w:before="40" w:after="60"/>
                <w:ind w:left="480" w:hanging="240"/>
            </w:pPr>
            <w:r>
                <w:rPr>
                    <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>
                    <w:color w:val="2563EB"/>
                    <w:b/>
                </w:rPr>
                <w:t xml:space="preserve">▪ </w:t>
            </w:r>
            {runs_xml}
        </w:p>
        """
        self.body_elements.append(xml)

    def add_callout(self, text, title="NOTE"):
        xml = f"""
        <w:p>
            <w:pPr>
                <w:pBdr>
                    <w:left w:val="single" w:sz="36" w:space="15" w:color="2563EB"/>
                </w:pBdr>
                <w:shd w:val="clear" w:color="auto" w:fill="F0F7FF"/>
                <w:spacing w:before="120" w:after="160"/>
                <w:ind w:left="240" w:right="240"/>
            </w:pPr>
            <w:r>
                <w:rPr>
                    <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>
                    <w:b/>
                    <w:sz w:val="20"/>
                    <w:color w:val="1E3A8A"/>
                </w:rPr>
                <w:t xml:space="preserve">[{escape(title)}] </w:t>
            </w:r>
            <w:r>
                <w:rPr>
                    <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>
                    <w:sz w:val="20"/>
                    <w:color w:val="1E293B"/>
                </w:rPr>
                <w:t xml:space="preserve">{escape(text)}</w:t>
            </w:r>
        </w:p>
        """
        self.body_elements.append(xml)

    def add_page_break(self):
        xml = """
        <w:p>
            <w:r>
                <w:br w:type="page"/>
            </w:r>
        </w:p>
        """
        self.body_elements.append(xml)

    def add_table(self, headers, rows, col_widths=None):
        tbl_pr = """
        <w:tblPr>
            <w:tblW w:w="9400" w:type="dxa"/>
            <w:jc w:val="center"/>
            <w:tblBorders>
                <w:top w:val="single" w:sz="6" w:space="0" w:color="CBD5E1"/>
                <w:left w:val="single" w:sz="6" w:space="0" w:color="CBD5E1"/>
                <w:bottom w:val="single" w:sz="8" w:space="0" w:color="94A3B8"/>
                <w:right w:val="single" w:sz="6" w:space="0" w:color="CBD5E1"/>
                <w:insideH w:val="single" w:sz="4" w:space="0" w:color="E2E8F0"/>
                <w:insideV w:val="single" w:sz="4" w:space="0" w:color="E2E8F0"/>
            </w:tblBorders>
            <w:tblCellMar>
                <w:top w:w="120" w:type="dxa"/>
                <w:left w:w="160" w:type="dxa"/>
                <w:bottom w:w="120" w:type="dxa"/>
                <w:right w:w="160" w:type="dxa"/>
            </w:tblCellMar>
        </w:tblPr>
        """
        
        # Header Row
        header_xml = "<w:tr><w:trPr><w:tblHeader/></w:trPr>"
        for i, h in enumerate(headers):
            w_xml = f'<w:tcW w:w="{col_widths[i]}" w:type="dxa"/>' if col_widths and i < len(col_widths) else ''
            header_xml += f"""
            <w:tc>
                <w:tcPr>
                    {w_xml}
                    <w:shd w:val="clear" w:color="auto" w:fill="1E3A8A"/>
                    <w:vAlign w:val="center"/>
                </w:tcPr>
                <w:p>
                    <w:pPr><w:spacing w:before="60" w:after="60"/></w:pPr>
                    <w:r>
                        <w:rPr>
                            <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>
                            <w:b/>
                            <w:sz w:val="20"/>
                            <w:color w:val="FFFFFF"/>
                        </w:rPr>
                        <w:t>{escape(h)}</w:t>
                    </w:r>
                </w:p>
            </w:tc>
            """
        header_xml += "</w:tr>"

        # Data Rows
        rows_xml = ""
        for row_idx, r in enumerate(rows):
            bg_color = "F8FAFC" if row_idx % 2 == 1 else "FFFFFF"
            rows_xml += "<w:tr>"
            for c_idx, cell_value in enumerate(r):
                w_xml = f'<w:tcW w:w="{col_widths[c_idx]}" w:type="dxa"/>' if col_widths and c_idx < len(col_widths) else ''
                rows_xml += f"""
                <w:tc>
                    <w:tcPr>
                        {w_xml}
                        <w:shd w:val="clear" w:color="auto" w:fill="{bg_color}"/>
                        <w:vAlign w:val="center"/>
                    </w:tcPr>
                    <w:p>
                        <w:pPr><w:spacing w:before="40" w:after="40"/></w:pPr>
                        <w:r>
                            <w:rPr>
                                <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>
                                <w:sz w:val="18"/>
                                <w:color w:val="1E293B"/>
                            </w:rPr>
                            <w:t>{escape(cell_value)}</w:t>
                        </w:r>
                    </w:p>
                </w:tc>
                """
            rows_xml += "</w:tr>"

        tbl_xml = f"""
        <w:tbl>
            {tbl_pr}
            {header_xml}
            {rows_xml}
        </w:tbl>
        <w:p><w:pPr><w:spacing w:before="120" w:after="120"/></w:pPr></w:p>
        """
        self.body_elements.append(tbl_xml)

    def build_docx(self, output_path):
        content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>"""

        root_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

        doc_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

        styles_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:docDefaults>
    <w:rPrDefault>
      <w:rPr>
        <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:eastAsia="Calibri" w:cs="Calibri"/>
        <w:sz w:val="22"/>
        <w:lang w:val="en-US"/>
      </w:rPr>
    </w:rPrDefault>
  </w:docDefaults>
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
  </w:style>
</w:styles>"""

        body_inner = "\n".join(self.body_elements)
        document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    {body_inner}
    <w:sectPr>
      <w:pgSz w:w="12240" w:h="15840"/>
      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/>
    </w:sectPr>
  </w:body>
</w:document>"""

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as docx:
            docx.writestr('[Content_Types].xml', content_types)
            docx.writestr('_rels/.rels', root_rels)
            docx.writestr('word/_rels/document.xml.rels', doc_rels)
            docx.writestr('word/styles.xml', styles_xml)
            docx.writestr('word/document.xml', document_xml)

        print(f"✓ Word document successfully generated: {output_path}")

print("DocxBuilder initialized.")
