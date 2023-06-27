from collections import defaultdict
from functools import reduce

from django.db import transaction
from django_elasticsearch_dsl_drf.utils import DictionaryProxy
from rest_framework import serializers
from rest_framework.reverse import reverse as api_reverse
from django_elasticsearch_dsl_drf.serializers import DocumentSerializer

from .conversion_documents import ConvertCaseDocument
from .serializers import ListSerializerWithCaseAllowance, CaseAllowanceMixin
from capweb.helpers import reverse


# CaseDocumentSerializers for new Convert and Export to S3 functionality
class ConvertBaseDocumentSerializer(DocumentSerializer):
    _abstract = True

    def __init__(self, *args, **kwargs):
        """
        If we are instantiated with an Elasticsearch wrapper object, convert to a bare dictionary.
        """
        super().__init__(*args, **kwargs)
        if isinstance(self.instance, ConvertCaseDocument):
            self.instance = self.instance._d_
        elif isinstance(self.instance, DictionaryProxy):
            self.instance = self.instance.to_dict()

    def s_from_instance(self, instance):
        # breakpoint()
        if "_source" in instance:
            return instance["_source"]
        elif type(instance) is ConvertCaseDocument:
            return instance._d_
        else:
            return instance


class ConvertCaseDocumentSerializer(ConvertBaseDocumentSerializer):
    class Meta:
        document = ConvertCaseDocument

    _url_templates = None

    def to_representation(self, instance):
        """
        Convert ES result to output dictionary for the API.
        """
        # cache url templates to avoid lookups for each object serialized
        if not self._url_templates:

            def placeholder_url(name):
                return api_reverse(name, ["REPLACE"]).replace("REPLACE", "%s")

            cite_home = reverse("cite_home", host="cite").rstrip("/")
            ConvertCaseDocumentSerializer._url_templates = {
                "case_url": placeholder_url("cases-detail"),
                "frontend_url": cite_home + "%s",
                "frontend_pdf_url": cite_home + "%s",
                "court_url": placeholder_url("court-detail"),
                "jurisdiction_url": placeholder_url("jurisdiction-detail"),
            }

        def as_dict(obj):
            if type(obj) == dict:
                return obj
            return obj._d_

        si = self.s_from_instance(instance)

        # get extracted_citations list, removing duplicate c["cite"] values
        extracted_citations = []
        ec = [
            o["extracted_citations"]
            for o in si["casebody_data"]["text"]["opinions"]
            if "extracted_citations" in o
        ]
        ec = [item for sublist in ec for item in sublist]
        for c in ec:
            c = as_dict(c)
            extracted_cite = {
                "cite": c["cite"],
                "category": c.get("category"),
                "reporter": c.get("reporter"),
            }
            if c.get("target_cases"):
                extracted_cite["case_ids"] = c["target_cases"]
            if int(c.get("weight", 1)) > 1:
                extracted_cite["weight"] = int(c["weight"])
            if c.get("year"):
                extracted_cite["year"] = c["year"]
            if c.get("pin_cites"):
                extracted_cite["pin_cites"] = c["pin_cites"]
            if isinstance(c.get("opinion_id"), int):
                extracted_cite["opinion_id"] = c["opinion_id"] - 1
            extracted_citations.append(extracted_cite)

        # move head_matter outside of casebody_data
        head_matter = list(
            filter(
                lambda x: x["type"] == "head_matter",
                si["casebody_data"]["text"]["opinions"],
            )
        )
        head_matter = head_matter[0] if head_matter else []
        if head_matter:
            si["casebody_data"]["text"]["opinions"].remove(head_matter)

        if "text" in head_matter:
            si["casebody_data"]["text"]["head_matter"] = head_matter["text"]

        # strip citations from casebody data
        for i, element in enumerate(s["casebody_data"]["text"]["opinions"]):
            if "extracted_citations" in element:
                del si["casebody_data"]["text"]["opinions"][i]["extracted_citations"]

        # IMPORTANT: If you change what values are exposed here, also change the "CaseLastUpdate triggers"
        # section in set_up_postgres.py to keep Elasticsearch updated.
        return {
            "id": si["id"],
            "url": self._url_templates["case_url"] % si["id"],
            "name": si["name"],
            "name_abbreviation": si["name_abbreviation"],
            "decision_date": si["decision_date_original"],
            "docket_number": si["docket_number"],
            "first_page": si["first_page"],
            "last_page": si["last_page"],
            "first_page_order": si["first_page_order"],
            "last_page_order": si["last_page_order"],
            "citations": [
                {"type": c["type"], "cite": c["cite"]} for c in s["citations"]
            ],
            "court": {
                "url": self._url_templates["court_url"] % s["court"]["slug"],
                "name_abbreviation": s["court"]["name_abbreviation"],
                "slug": s["court"]["slug"],
                "id": s["court"]["id"],
                "name": s["court"]["name"],
            },
            "jurisdiction": {
                "id": s["jurisdiction"]["id"],
                "name_long": s["jurisdiction"]["name_long"],
                "url": self._url_templates["jurisdiction_url"]
                % s["jurisdiction"]["slug"],
                "slug": s["jurisdiction"]["slug"],
                "whitelisted": s["jurisdiction"]["whitelisted"],
                "name": s["jurisdiction"]["name"],
            },
            "cites_to": extracted_citations,
            "frontend_url": self._url_templates["frontend_url"] % s["frontend_url"],
            "frontend_pdf_url": self._url_templates["frontend_pdf_url"]
            % s["frontend_pdf_url"]
            if s["frontend_pdf_url"]
            else None,
            "analysis": s.get("analysis", {}),
            "last_updated": s["last_updated"] or s["provenance"]["date_added"],
            "provenance": s["provenance"],
        }


class ConvertCaseDocumentSerializerWithCasebody(
    CaseAllowanceMixin, ConvertCaseDocumentSerializer
):
    class Meta:
        document = ConvertCaseDocument
        list_serializer_class = ListSerializerWithCaseAllowance

    def to_representation(self, instance):
        case = super().to_representation(instance)
        request = self.context.get("request")
        s = self.s_from_instance(instance)

        # render case
        data = None
        body_format = self.context.get("force_body_format") or request.query_params.get(
            "body_format"
        )
        if body_format not in ("html", "xml"):
            body_format = "text"
        data = s["casebody_data"][body_format]

        case["casebody"] = data
        return case


class NoLoginConvertCaseDocumentSerializer(ConvertCaseDocumentSerializerWithCasebody):
    def to_representation(self, instance):
        """Tell get_casebody not to check for case download permissions."""
        return super().to_representation(instance)

    @property
    def data(self):
        """Skip tracking of download counts."""
        return super(DocumentSerializer, self).data
