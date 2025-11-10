"""
Created on 11.02.2020
__updated__ = "2024-02-23"
@author: Wolfgang Kramer

Extensions of project fints source code  copied and modified
    Pure-python FinTS (formerly known as HBCI) implementation https://pypi.python.org/pypi/fints
"""

from fints.fields import DataElementField, DataElementGroupField, CodeField
from fints.formals import DataElementGroup, KTI1
from fints.segments.base import ParameterSegment, ParameterSegment_22, FinTS3Segment
from fints.utils import RepresentableEnum, doc_enum


@doc_enum
class DeliveryType(RepresentableEnum):
    """Art der Lieferung Payment Status Report """
    S = 'S'  # doc: schrittweise Lieferung
    V = 'V'  # doc: vollständige Lieferung


@doc_enum
class VopTestResult(RepresentableEnum):
    """VOP Prüfergebnis version 1

    Source: FinTS Financial Transaction Services,
             Verification of Payee
             Data Dictionary

    """

    MATCH = 'RCVC'  # doc: Übereinstimmung des angefragten Namens
    NO_MATCH = 'RVNM'  # doc: Keine Übereinstimmung des angefragten Namens
    CLOSE_MATCH = 'RVMC'  # doc: Teilweise Übereinstimmung des angefragten Namens
    NOT_APPLICABLE = 'RVNA'  # doc: Zahlungsdienstleister führt
    PENDING = 'PDNG'  # doc: Antwort des Zahlungsdienstleisters steht noch aus


class PaymentStatusReport(DataElementGroup):
    """
    Parameter not implemented in GitHub Project FinTS (see module fints.formals)

    Version 1
    Source: FinTS Financial Transaction Services, Verification of Payee,
            SEPA-Zahlungsverkehr  -- Namensabgleich (Verification of Payee)
    """
    polling_id = DataElementField(
        type='bin', required=False, _d='Aufsetzpunkt belegt  und vom Institut wurde eine Polling-ID geliefert')
    number_entries_allowed = DataElementField(type='jn', required=False, _d='Eingabe Anzahl Eintraege erlaubt')
    touchdown_point = DataElementField(type='an', max_length=35, required=False, _d="Aufsetzpunkt")


class ResultPaymentStatusReport(DataElementGroup):
    """
    Parameter not implemented in GitHub Project FinTS (see module fints.formals)

    Liefert die Ergebnisse der VOP-Prüfung an den Kunden im Falle einer Ein
    zeltransaktion zurück. Diese DEG stellt lediglich eine Alternative zur Lieferung
    in einer pain.002 dar

    Version 1
    Source: FinTS Financial Transaction Services, Verification of Payee,
            SEPA-Zahlungsverkehr  -- Namensabgleich (Verification of Payee)
    """
    iban = DataElementField(type='an', max_length=34, _d="IBAN Empfänger")
    iban_info = DataElementField(type='an', max_length=140, required=False, _d="IBAN Zusatzinformation")
    different_name = DataElementField(type='an', max_length=140, required=False, _d="Abweichender Empfängername")
    other_identification_feature = DataElementField(type='an', max_length=256, required=False, _d="Anderes Identifikationsmerkmal")
    vop_test_result = CodeField(enum=VopTestResult, length=4)
    reason_RVNA = DataElementField(type='an', max_length=256, required=False, _d="Grund RVNA")


class ParameterVerificationPayee(DataElementGroup):
    """
    Parameter not implemented in GitHub Project FinTS (see module fints.formals)

    Parameter Namensabgleich Prüfauftrag
              Auftragsspezifische Bankparameterdaten für den Geschäftsvorfall „Namensabgleich Prüfauftrag“.

    Source:
        Financial Transaction Services (FinTS)
        Dokument: Verification of Payee
        Kapitel: Data Dictionary
        Abschnitt: Data Dictionary


    """
    max_number_credit = DataElementField(
        type='num', length=7, _d='Maximale Anzahl CreditTransferTransactionInformation Opt-In')
    explanatory_text = DataElementField(type='jn', _d='Aufklärungstext strukturiert')
    type_delivery = CodeField(enum=VopTestResult, length=4)
    collective_payment = DataElementField(type='jn', _d='Sammelzahlungen mit einem Auftrag erlaubt')
    number_entries_allowed = DataElementField(type='jn', _d='Eingabe Anzahl Eintraege erlaubt')
    supported_formats = DataElementField(type='an', max_length=1024, _d='Unterstützte Payment Status Report Datenformate')
    mandatory_vop_formats = DataElementField(type='an', max_length=6, max_count=99, _d="VOP-pflichtiger Zahlungsverkehrsauftrag")


class ParameterAccountTurnoverPeriod(DataElementGroup):
    """
    Parameter not implemented in GitHub Project FinTS (see module fints.formals)
    """

    """ Parameter       Kontoumsaetze
                        Zeitraum
    Source: FinTS Financial Transaction Services, Schnittstellenspezifikation,
            Messages -- Geschaeftsvorfaelle
    """
    storage_period = DataElementField(
        type='num', max_length=4, _d='Speicherzeitraum')
    number_entries_allowed = DataElementField(
        type='jn', _d='Eingabe Anzahl Eintraege erlaubt')
    all_accounts = DataElementField(type='jn', _d='Alle Konten')


class SecuritiesReferenceType(RepresentableEnum):
    """
    Wertpapier Referenzart, version 2
      Wertpapierreferenz, ueber die z.B. eine Umsatzanfrage auf ein bestimmtes
      Papier eingeschraenkt werden kann.

    Source: FinTS Financial Transaction Services, Schnittstellenspezifikation,
            Messages -- Multibankfaehige
    """
    ISIN = '1'  # :     ISIN
    WKN = '2'  # :     Wertpapierkennziffer
    INTERNAL = '3'  # :     kreditinstitutsinterne Referenz
    INDEXNAME = '4'  # :      Indexname


class SecuritiesReference(DataElementGroup):
    """
    Referenzart Art der Referenzierung auf Wertpapierinformationen.
    Codierung: 1: ISIN 2: WKN 3: kreditinstitutsinterne Referenz 4: Indexname

    Wertpapiercode Wertpapiercode gemaess der Referenzart (DE Referenzart).
    Im Fall der ISIN erfolgt die Angabe 12-stellig alphanumerisch,
    im Fall der WKN 6-stellig numerisch (zukuenftig auch alphanumerisch).
    Es wird dem Kunden diejenige Referenz zurueckgemeldet, die er im Auftrag angegeben hat.
    """
    securities_reference_type = CodeField(
        enum=SecuritiesReferenceType, length=1, _d='Bezeichnung des TAN-Medium erforderlich')
    securities_code = DataElementField(
        type='an', max_length=30, required=True, _d='Wertpapiercode')


class HIKAZS6(ParameterSegment):
    """
    Segment not implemented in Project FinTS (see module fints.segments.statement)
    """

    """Kontoumsaetze Zeitraum, Bankparameterdaten, version 6

    Source: FinTS Financial Transaction Services, Schnittstellenspezifikation,
            Messages -- Multibankfaehige Geschaeftsvorfaelle
    """
    parameter = DataElementGroupField(
        type=ParameterAccountTurnoverPeriod, _d='Parameter Kontoumsaetze/Zeitraum')


class HIKAZS7(ParameterSegment):
    """
    Segment not implemented in Project FinTS (see module fints.segments.statement)
    """

    """Kontoumsaetze Zeitraum, Bankparameterdaten, version 7

    Source: FinTS Financial Transaction Services, Schnittstellenspezifikation,
            Messages -- Multibankfaehige Geschaeftsvorfaelle
    """
    parameter = DataElementGroupField(
        type=ParameterAccountTurnoverPeriod, _d='Parameter Kontoumsaetze/Zeitraum')


class HIWPDS5(ParameterSegment_22):
    """
    Segment not implemented in Project FinTS (see module fints.segments.depot)
    """
    pass


class HIWPDS6(ParameterSegment):
    """
    Segment not implemented in Project FinTS (see module fints.segments.depot)
    """
    pass


class HKCSE1(FinTS3Segment):
    """
    SEPA Namensabgleich Prüfauftrag Version 1

    Source: FinTS Financial Transaction Services, Verification of Payee,
            Messages -- Multibankfaehige Geschaeftsvorfaelle
    """

    account = DataElementGroupField(
        type=KTI1, _d='Kontoverbindung international')
    sepa_descriptor = DataElementField(
        type='an', max_length=256, _d='SEPA Descriptor')
    sepa_pain_message = DataElementField(type='bin', _d='SEPA pain message')


class _HKVPP(FinTS3Segment):
    """
        Segment not implemented in Project FinTS

        Name: Namensabgleich Prüfauftrag
        Typ: Segment
        Segmentart: Geschäftsvorfall
        Kennung: HKVPP
        Bezugssegment: -
        Version: 1
        Sender: Kunde

    Source: Financial Transaction Services (FinTS)
            Dokument: Verification of Payee
            Kapitel: SEPA-Zahlungsverkehr
            Abschnitt: Namensabgleich (Verification of Payee)
    """
    reports = DataElementGroupField(
        type=PaymentStatusReport, _d='Unterstützte Payment Status Reports')
    polling_id = DataElementField(type='bin', _d='Ergebnis der VOP Prüfung Einzeltransaktion')
    max_number_responses = DataElementField(type='num', max_length=4, required=False, _d="Maximale Anzahl Einträge")
    touchdown_point = DataElementField(type='an', max_length=35, required=False, _d="Aufsetzpunkt")


class HKVPP(FinTS3Segment):
    """Dummy HKVPP Segment für Atruvia-Server."""

    type = "HKVPP"
    version = 3

    fields = [
        ("aktiv_flag", DataElementField),
    ]

    def __init__(self, aktiv_flag="0", segment_no=None):
        # NICHT super().__init__(...) aufrufen!
        self.segment_no = segment_no
        self.aktiv_flag = aktiv_flag
        
        
class HIVPP(FinTS3Segment):
    """
        Segment not implemented in Project FinTS

        Name: Namensabgleich Prüfergebnis
        Typ: Segment
        Segmentart: Geschäftsvorfall
        Kennung: HIVPP
        Bezugssegment: HKVPP
        Version: 1
        Anzahl: 1
        Sender: Kreditinstitut

    Source: Financial Transaction Services (FinTS)
            Dokument: Verification of Payee
            Kapitel: SEPA-Zahlungsverkehr
            Abschnitt: Namensabgleich (Verification of Payee)
    """
    vop_id = DataElementField(type='bin', _d='Ergebnis der VOP Prüfung Einzeltransaktion')
    vop_id_valid_to = DataElementField(type='dat', required=False, _d='VOP-ID gültig bis')
    polling_id = DataElementField(type='bin', _d='Ergebnis der VOP Prüfung Einzeltransaktion')
    status_descriptor = DataElementField(type='an', max_length=256, required=False, _d='Payment Status Report Descriptor')
    status_report = DataElementField(type='bin', _d='Ergebnis der VOP Prüfung Einzeltransaktion')
    test_result = DataElementGroupField(type=ResultPaymentStatusReport, _d='Ergebnis VOP-Prüfung Einzeltransaktion')
    explanatory_text = DataElementField(type='an', max_length=65535, required=False, _d='Aufklärungstext Autorisierung trotz Abweichung')
    waiting = DataElementField(type='num', length=1, required=False, _d='Wartezeit nächste Abfrage')


class HIVPPS(FinTS3Segment):
    """
        Segment not implemented in Project FinTS

        Name: Namensabgleich Prüfauftrag Parameter
        Typ: Segment
        Segmentart: Geschäftsvorfall
        Kennung: HIVPPS
        Bezugssegment: HKVVB
        Version: 1
        Sender: Kreditinstitut

    Source:
        Financial Transaction Services (FinTS)
        Dokument: Verification of Payee
        Kapitel:  SEPA-Zahlungsverkehr
        Abschnitt: Namensabgleich (Verification of Payee)
    """
    max_number_entries = DataElementField(type='num', max_length=3, _d='Maximale Anzahl Aufträge')
    number_signatures = DataElementField(type='num', max_length=1, _d='Anzahl Signaturen midestens')
    security_class = CodeField(enum=DeliveryType, length=1, _d='Sicherheitsklasse')
    prameter = DataElementGroupField(
        type=ParameterVerificationPayee, _d='Parameter Namensabgleich Prüfauftrag ')


class HKVPA(FinTS3Segment):
    """
        Segment not implemented in Project FinTS

        Name: Namensabgleich Ausführungsauftrag
        Typ: Segment
        Segmentart: Geschäftsvorfall
        Kennung: HKVPA
        Bezugssegment: -
        Version: 1
        Sender: Kunde

    Source: Financial Transaction Services (FinTS)
            Dokument: Verification of Payee
            Kapitel: SEPA-Zahlungsverkehr
            Abschnitt: Namensabgleich (Verification of Payee)
    """
    vop_id = DataElementField(type='bin', _d='Ergebnis der VOP Prüfung Einzeltransaktion')


class HIVPAS(FinTS3Segment):
    """
        Segment not implemented in Project FinTS

        Name: Namensabgleich Ausführungsauftrag Parameter
        Typ: Segment
        Segmentart: Geschäftsvorfall
        Kennung: HIVPAS
        Bezugssegment: HKVVB
        Version: 1
        Sender: Kreditinstitut

    Source:
        Financial Transaction Services (FinTS)
        Dokument: Verification of Payee
        Kapitel:  SEPA-Zahlungsverkehr
        Abschnitt: Namensabgleich (Verification of Payee)
    """
    max_number_entries = DataElementField(type='num', max_length=3, _d='Maximale Anzahl Aufträge')
    number_signatures = DataElementField(type='num', max_length=1, _d='Anzahl Signaturen midestens')
    security_class = CodeField(enum=DeliveryType, length=1, _d='Sicherheitsklasse')
