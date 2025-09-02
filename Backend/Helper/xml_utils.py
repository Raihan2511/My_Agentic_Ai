from lxml import etree

class XMLValidator:
    def __init__(self, dtd: etree.DTD):
        self.dtd = dtd

    def validate_and_repair(self, xml: str) -> str:
        parser = etree.XMLParser(recover=True, remove_blank_text=True)
        try:
            root = etree.fromstring(xml.encode("utf-8"), parser=parser)
        except Exception:
            root = etree.fromstring(f"<wrapper>{xml}</wrapper>".encode("utf-8"), parser=parser)

        tree = etree.ElementTree(root)
        if self.dtd.validate(tree):
            return etree.tostring(root, pretty_print=True, encoding="unicode")

        # minimal auto-repair heuristic
        if len(root) == 0:
            etree.SubElement(root, "notes").text = ""

        return etree.tostring(root, pretty_print=True, encoding="unicode")
