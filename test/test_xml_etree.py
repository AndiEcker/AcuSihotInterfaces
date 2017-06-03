import pytest
from xml.etree.ElementTree import XMLParser, ParseError

header = '<?xml version="1.0" encoding="{}"?>\n<TEST-Document>\n'

# chr index, xml, ALT-key+leading_zero, Alt-key
special_chars = [
    [1, '&#1;', '', '☺'],
    [7, '&#7;', '', '•'],
    [10, '&#10;', '\n', ''],
    [13, '&#13;', '\r', ''],
    [36, '&#36;', '$', '$'],
    [40, '&#40;', '(', '('],
    [41, '&#41;', ')', ')'],
    [61, '&#61;', '=', '='],
    [91, '&#91;', '[', '['],
    [92, '&#92;', '\\', '\\'],
    [93, '&#93;', ']', ']'],
    [99, '&#99;', 'c', 'c'],
    [123, '&#123;', '{', '{'],
    [128, '&#128;', '€', 'Ç'],
    [161, '&#161;', '¡', 'í'],
    [191, '&#191;', '¿', '┐'],
    [193, '&#193;', 'Á', '┴'],
    [196, '&#196;', 'Ä', '─'],
    [197, '&#197;', 'Å', '┼'],
    [201, '&#201;', 'É', '╔'],
    [211, '&#211;', 'Ó', '╙'],
    [216, '&#216;', 'Ø', '╪'],
    [223, '&#223;', 'ß', '▀'],
    [224, '&#224;', 'à', 'α'],
    [225, '&#225;', 'á', 'ß'],
    [228, '&#228;', 'ä', 'Σ'],
    [229, '&#229;', 'å', 'σ'],
    [230, '&#230;', 'æ', 'µ'],
    [232, '&#232;', 'è', 'Φ'],
    [233, '&#233;', 'é', 'Θ'],
    [237, '&#237;', 'í', 'φ'],
    [239, '&#239;', 'ï', '∩'],
    [241, '&#241;', 'ñ', '±'],
    [243, '&#243;', 'ó', '≤'],
    [246, '&#246;', 'ö', '÷'],
    [248, '&#248;', 'ø', '°'],
    [250, '&#250;', 'ú', '·'],
    [252, '&#252;', 'ü', 'ⁿ'],
]

footer = '\n</TEST-Document>'

full_text = 'test string with special characters: ' + \
            ' '.join([str(sc[0]) + '=' + chr(sc[0]) + sc[1] + sc[2] + sc[3] for sc in special_chars])


class TestParseErrorExceptions:
    def test_parse_errors_without_header_footer(self):
        parser = XMLParser(target=self)
        with pytest.raises(ParseError):
            parser.feed(full_text)

    def test_parse_errors_with_empty_encoding(self):
        parser = XMLParser(target=self)
        with pytest.raises(ParseError):
            parser.feed(header.format('') + full_text + footer)

    def test_parse_errors_with_encoding_and_invalid_chars(self):
        parser = XMLParser(target=self)
        with pytest.raises(ParseError):
            parser.feed(header.format('cp1252') + full_text + footer)  # chr(1) and chr(7) are invalid

    def test_parse_errors_single_char(self):
        for enc in ['cp1252', 'utf8', 'ISO-8859-1']:
            for sc in special_chars:
                t = header.format(enc) + chr(sc[0]) + sc[1] + sc[2] + sc[3] + footer
                print(t)
                parser = XMLParser(target=self)
                if sc[0] in (1, 7):
                    print(' ****  exception expected  ****')
                    with pytest.raises(ParseError):
                        parser.feed(t)
                else:
                    parser.feed(t)
