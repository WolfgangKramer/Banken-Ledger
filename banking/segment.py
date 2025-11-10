"""
Created on 18.11.2019
__updated__ = "2025-05-31"
@author: Wolfgang Kramer
"""

from PIL import Image
from io import BytesIO

from datetime import datetime, date, timedelta

from fints.formals import (
    AlgorithmParameterIVName, AlgorithmParameterName,
    BankIdentifier,
    CompressionFunction,
    DateTimeType,
    EncryptionAlgorithm, EncryptionAlgorithmCoded,
    HashAlgorithm,
    IdentifiedRole,
    KeyName, KeyType,
    Language2,
    OperationMode,
    SecurityApplicationArea, SecurityDateTime, SecurityIdentificationDetails, SecurityMethod,
    SecurityProfile, SecurityRole, SignatureAlgorithm, SystemIDStatus, SynchronizationMode,
    UsageEncryption, UserDefinedSignature,
)
from fints.message import FinTSCustomerMessage
from fints.models import SEPAAccount
from fints.segments.auth import HKIDN2, HKVVB3, HKTAN6, HKTAN7
from fints.segments.depot import HKWPD5, HKWPD6
from fints.segments.dialog import HKSYN3, HKEND1
from fints.segments.message import HNHBK3, HNHBS1, HNSHK4, HNSHA2, HNVSD1, HNVSK3
from fints.segments.statement import HKKAZ6, HKKAZ7
from fints.segments.transfer import HKCCS1
from fints.types import SegmentSequence

from banking.declarations import MESSAGE_TEXT, PNS, SYSTEM_ID_UNASSIGNED, WM_DELETE_WINDOW
from banking.fints_extension import HKCSE1, HKVPP
from banking.messagebox import (MessageBoxInfo, MessageBoxTermination)
from banking.forms import InputTAN


def encrypt(bank, message):
    now = datetime.now()
    plain_segments = message.segments[1:-1]
    del message.segments[1:-1]
    message.segments.insert(
        1,
        HNVSK3(
            security_profile=SecurityProfile(SecurityMethod.PIN, 2),
            security_function=998,
            security_role=SecurityRole.ISS,
            security_identification_details=SecurityIdentificationDetails(
                IdentifiedRole.MS,
                identifier=bank.security_identifier,
            ),
            security_datetime=SecurityDateTime(
                DateTimeType.STS,
                now.date(),
                now.time(),
            ),
            encryption_algorithm=EncryptionAlgorithm(
                UsageEncryption.OSY,
                OperationMode.CBC,
                EncryptionAlgorithmCoded.TWOKEY3DES,
                b'\x00' * 8,
                AlgorithmParameterName.KYE,
                AlgorithmParameterIVName.IVC,
            ),
            key_name=KeyName(
                BankIdentifier(
                    BankIdentifier.COUNTRY_ALPHA_TO_NUMERIC['DE'], bank.bank_code),
                bank.user_id,
                KeyType.V,
                0,
                0,
            ),
            compression_function=CompressionFunction.NULL,
        )
    )
    message.segments[1].header.number = 998
    message.segments.insert(
        2,
        HNVSD1(
            data=SegmentSequence(segments=plain_segments)
        )
    )
    message.segments[2].header.number = 999


def from_to_date(bank):
    if isinstance(bank.to_date, str):
        bank.to_date = date(
            int(bank.to_date[0:4]), int(bank.to_date[5:7]), int(bank.to_date[8:10]))
    if isinstance(bank.from_date, str):
        bank.from_date = date(
            int(bank.from_date[0:4]), int(bank.from_date[5:7]), int(bank.from_date[8:10]))
    if bank.to_date > date.today():
        bank.to_date = date.today()
    if bank.from_date > date.today():
        bank.from_date = date.today()
    if bank.to_date < bank.from_date:
        bank.from_date = bank.to_date
    _latest_date = date.today() - timedelta(bank.storage_period)
    if bank.to_date < _latest_date:
        bank.from_date = _latest_date
        bank.to_date = _latest_date
        if bank.period_message:
            return
        MessageBoxInfo(MESSAGE_TEXT['BANK_PERIOD'].format(
            bank.bank_name, bank.bank_code, bank.account_number, bank.account_product_name, _latest_date), bank=bank)
        bank.period_message = True  # trigger:  message is shown
    else:
        if bank.from_date < _latest_date:
            bank.from_date = _latest_date
            if bank.period_message:
                return
            MessageBoxInfo(MESSAGE_TEXT['BANK_PERIOD'].format(
                bank.bank_name, bank.bank_code, bank.account_number, bank.account_product_name, _latest_date), bank=bank)
            bank.period_message = True


def _get_segment(bank, segment_type):

    for seg in [HKTAN7, HKTAN6, HKKAZ7, HKKAZ6, HKWPD6, HKWPD5]:
        if (seg.__name__[2:5] == segment_type
                and seg.__name__[5:6] == str(bank.transaction_versions[segment_type])):
            return seg
    MessageBoxTermination(info=MESSAGE_TEXT['VERSION_TRANSACTION'].format(
        'HK', segment_type, bank.transaction_versions[segment_type]), bank=bank)
    return False  # thread checking


def _sepaaccount(bank):

    return SEPAAccount(iban=bank.iban, bic=bank.bic, accountnumber=bank.account_number,
                       subaccount=bank.subaccount_number, blz=bank.bank_code)


class Segments():
    """
    Segement for use in FinTS Messages
    """

    def segHNHBK(self, bank):
        """
        Segment Nachrichtenkopf
        
            Nachstehender Kopfteil fuehrt alle Kunden- und Kreditinstitutsnachrichten an.

        Financial Transaction Services (FinTS) 3.0
        Dokument: Formals
        Kapitel: Nachrichtenaufbau
        Abschnitt: Steuerstrukturen
        """
        message = FinTSCustomerMessage()
        message += HNHBK3(0, 300, bank.dialog_id, bank.message_number)
        return message

    def segHNSHK(self, bank, message):
        """
        Segment Signaturkopf
        
            Der Signaturkopf enthaelt Informationen ueber den damit verbundenen
            Sicherheitsservice, sowie ueber den Absender.

        Financial Transaction Services (FinTS) 3.0
        Dokument: Security - Sicherheitsverfahren HBCI
        Kapitel: Verfahrensbeschreibung
        Abschnitt: Formate fuer Signatur und Verschluesselung
        """
        now = datetime.now()
        message += HNSHK4(
            security_profile=SecurityProfile(SecurityMethod.PIN, 2),
            security_function=bank.security_function,
            security_reference=bank.security_reference,
            security_application_area=SecurityApplicationArea.SHM,
            security_role=SecurityRole.ISS,
            security_identification_details=SecurityIdentificationDetails(
                IdentifiedRole.MS,
                identifier=bank.security_identifier,
            ),
            security_reference_number=1,
            security_datetime=SecurityDateTime(
                DateTimeType.STS,
                now.date(),
                now.time(),
            ),
            hash_algorithm=HashAlgorithm(
                usage_hash='1',
                hash_algorithm='999',
                algorithm_parameter_name='1',
            ),
            signature_algorithm=SignatureAlgorithm(
                usage_signature='6',
                signature_algorithm='10',
                operation_mode='16',
            ),
            key_name=KeyName(
                BankIdentifier(
                    BankIdentifier.COUNTRY_ALPHA_TO_NUMERIC['DE'], bank.bank_code),
                bank.user_id,
                KeyType.S,
                0,
                0,
            ),
        )
        return message

    def segHKIND(self, bank, message, user_id=None):
        """
        Segment Identifikation

            Das Identifikations-Segment enthaelt Kontextinformationen, die fuer den gesamten Dialog
            Gueltigkeit haben. Anhand dieser Daten wird die Sendeberechtigung des Benutzers
            geprueft. Eine Pruefung der transportmedienspezifischen Kennung des Benutzers
            erfolgt nicht.
            Falls dem Benutzer die Berechtigung zum Senden weiterer Nachrichten nicht erteilt
            werden kann, ist ein entsprechender Rueckmeldungscode in die Kreditinstituts-
            antwort einzustellen. Es steht Kreditinstituten frei, in bestimmten Faellen auf eine
            Identifizierung des Kunden zu verzichten. Dies ist zum Beispiel fuer den anonymen
            Zugang (s.u.) erforderlich, wo mit einem Nichtkunden kommuniziert wird.

        Financial Transaction Services (FinTS) 3.0
        Dokument: Formals
        Kapitel: Dialogspezifikation
        Abschnitt: Dialoginitialisierung
        """
        if user_id is None:
            # its not a anonymous dialogue: user_id# CUSTOMER_ID_ANONYMOUS
            user_id = bank.user_id
        if bank.system_id == SYSTEM_ID_UNASSIGNED:
            system__id_status = SystemIDStatus.ID_UNNECESSARY
        else:
            system__id_status = SystemIDStatus.ID_NECESSARY
        message += HKIDN2(
            BankIdentifier(
                BankIdentifier.COUNTRY_ALPHA_TO_NUMERIC['DE'], bank.bank_code),
            user_id,
            bank.system_id,
            system_id_status=system__id_status
        )
        return message

    def segHKVVB(self, bank, message):
        """
        Segment Verarbeitungsvorbereitung

            Dieses Segment dient der uebermittlung von Informationen ueber das Kundensystem,
            mit Hilfe derer das Kreditinstitut individuell auf Anforderungen des Kunden reagieren
            kann.

        Financial Transaction Services (FinTS) 3.0
        Dokument: Formals
        Kapitel: Dialogspezifikation
        Abschnitt: Dialoginitialisierung
         """
        message += HKVVB3(
            bank.bpd_version,
            bank.upd_version,
            Language2.DE,
            bank.product_id,
            '0'
        )
        return message

    def segHKTAN_decoupled(self, bank, message, segment_name='HKKAZ'):
        """
        Segment Geschaeftsvorfall HITAN7 (starke Kundenauthentifizierung)

            Ab der Segmentversion #7 dieses Geschaeftsvorfalls wird das Decoupled-Verfahren
            mit Freigabe des Auftrags auf einem separaten Geraet unterstuetzt. Das Decoupled
            Verfahren kommt ohne TAN-Erzeugung und Eingabe aus und ist somit kein TAN
            Verfahren mehr, es bedient sich aber der Mechanismen und Felder bisheriger TAN
            Verfahren im HKTAN. Im Kontext des Decoupled-verfahrens ist bei der Verwendung
            des Begriffs TAN im uebertragenen Sinne die Freigabe/Bestaetigung einer Transaktion
            gemeint: z.B „Bezeichnung des TAN-Mediums“ -> „Bezeichnung des Freigabe
            Mediums“. Die Begrifflichkeiten in Rahmen dieses Geschaeftsvorfalls orientieren sich
            trotzdem weiterhin an den klassischen TAN-Verfahren. Eine Umbenennung der Felder erfolgt nicht.

        Financial Transaction Services (FinTS)
        Dokument: Security - Sicherheitsverfahren PIN/TAN
        Kapitel: Verfahrensbeschreibung
        Abschnitt: Geschaeftsvorfall HKTAN fuer Zwei-Schritt-TAN-Einreichung
        """
        if bank.task_reference == 'noref':
            bank.task_reference = None
        try:
            hktan = _get_segment(bank, 'TAN')
        except Exception:
            hktan = HKTAN6
        message += hktan(
            'S',
            task_reference=bank.task_reference,
            further_tan_follows=False,
        )
        return message

    def segHKTAN(self, bank, message, segment_name='HKIDN'):
        """
        Segment Geschaeftsvorfall HITAN6/7 (starke Kundenauthentifizierung)

            Dieser Geschaeftsvorfall dient im Zwei-Schritt-Verfahren dazu, eine Challenge zur
            TAN-Bildung anzufordern und eine TAN zu einem Auftrag zu uebermitteln.

        Financial Transaction Services (FinTS)
        Dokument: Security - Sicherheitsverfahren PIN/TAN
        Kapitel: Verfahrensbeschreibung
        Abschnitt: Geschaeftsvorfall HKTAN fuer Zwei-Schritt-TAN-Einreichung
        """
        if bank.task_reference == 'noref':
            bank.task_reference = None
        try:
            hktan = _get_segment(bank, 'TAN')
        except Exception:
            hktan = HKTAN6
        message += hktan(
            bank.tan_process,
            segment_name,
            task_reference=bank.task_reference,
            further_tan_follows=False,
            tan_medium_name=bank.security_function
        )
        return message

    def segHKSYN(self, bank, message):
        """
        Segment Synchronisierung

            Bevor ein Benutzer bei Verwendung des PIN/TAN-Verfahrens von einem neuen
            Kundensystem Auftraege erteilen kann, hat er im Wege einer Synchronisierung
            eine Kundensystem-ID fuer dieses System anzufordern.
            Diese ID ist im Folgenden stets anzugeben, wenn der Benutzer von diesem Kundensystem
            aus Nachrichten sendet.
            Wenn eine Synchronisierung der Kundensystem-ID durchgefuehrt wird,  ist das DE
            >Kundensystem-ID< mit dem Wert 0 zu belegen. Das DE >Identifizierung der Partei<
            im Signaturkopf in der DEG <Sicherheitsidentifikation,
            Details< ist mit dem Wert  0 zu belegen.

        Financial Transaction Services (FinTS)
        Dokument: Formals
        Kapitel: Dialogspezifikation
        Abschnitt: Synchronisierung
        """
        message += HKSYN3(SynchronizationMode.NEW_SYSTEM_ID)
        return message

    def segHKKAZ(self, bank, message):
        """
        Segment Kontoumsaetze/Zeitraum

            Die Loesung bietet dem Kunden die Moeglichkeit, auf seinem System verlorengegangene
            Buchungen erneut zu erhalten.
            Der maximale Zeitraum, fuer den rueckwirkend Buchungen beim Kreditinstitut gespeichert
            sind, wird in den Bankparameterdaten uebermittelt.

            Kreditinstitutsrueckmeldung:
            Eine Buchungsposition besteht aus einem :61:/:86:-Block eines MT 940Formats.
            Es muss davon unabhaengig immer ein gueltiges MT 940-Format zurueckgemeldet werden,
            d.h. die Felder :20: bis :60: und :62: bis :86: sind obligatorischer Bestandteil
            der Rueckmeldung.

        Financial Transaction Services (FinTS)
        Dokument: Messages - Multibankfaehige Geschaeftsvorfaelle
        Kapitel: Geschaeftsvorfaelle
        Abschnitt: Konto- und Umsatz-Informationen
        """
        from_to_date(bank)
        hkkaz = _get_segment(bank, 'KAZ')
        if hkkaz in [HKKAZ6, HKKAZ7]:
            message += hkkaz(
                account=hkkaz._fields['account'].type.from_sepa_account(
                    _sepaaccount(bank)),
                all_accounts=False,
                date_start=bank.from_date,
                date_end=bank.to_date
            )
            return message
        MessageBoxTermination(info=MESSAGE_TEXT['HIKAZ'].format(
            bank.bank_name, bank.account_number, bank.account_product_name), bank=bank)

    def segHKWPD(self, bank, message):
        """
        Segment Depotaufstellung anfordern

            Die Depotaufstellung kann beliebige Papiere, auch in Fremdwaehrungen, umfassen.

            Kreditinstitutsrueckmeldung:
            Es ist das S.W.I.F.T.-Format MT 535 in der Version SRG 1998 (s. [Datenformate])
            einzustellen.

        Financial Transaction Services (FinTS)
        Dokument: Messages - Multibankfaehige Geschaeftsvorfaelle
        Kapitel: Geschaeftsvorfaelle
        Abschnitt: Wertpapiere
        """
        hkwpd = _get_segment(bank, 'WPD')
        message += hkwpd(
            account=hkwpd._fields['account'].type.from_sepa_account(
                _sepaaccount(bank))
        )
        return message

    def segHKCCS1(self, bank, message):
        """
        Segment Einzelueberweisung

            Fuer Einzelueberweisungsauftraege auf der Basis der pain.001.001.02 ist nur die
             Grouping Option Grouped mit genau einer Einzeltransaktion
             CreditTransferTransactionInformation >CdtTrfTxInf< zugelassen.

            Belegungsrichtlinien
            Kontoverbindung international IBAN und BIC muessen der IBAN in
            DebtorAccount bzw. der BIC in DebtorAgent entsprechen.
            SEPA pain message: Erlaubtes SEPA-Ueberweisungg-Kunde-Bank-Schema lt HISPAS.
            In das Mussfeld RequestedExecutionDate ist 1999-01-01 einzustellen.

        Financial Transaction Services (FinTS)
        Dokument: Messages - Multibankfaehige Geschaeftsvorfaelle
        Kapitel: Geschaeftsvorfaelle
        Abschnitt: Einzelueberweisung
        """
        if bank.bank_code=='72090000':
            message += HKVPP(segment_no=2)                
        hkcss = HKCCS1
        message += hkcss(
            account=hkcss._fields['account'].type.from_sepa_account(
                _sepaaccount(bank)),
            sepa_descriptor=bank.sepa_descriptor,
            sepa_pain_message=bank.sepa_credit_transfer_data,
        )
        return message

    def segHKCSE1(self, bank, message):
        """
        Segment Terminierte Einzelueberweisung

            Fuer Einzelueberweisungsauftraege auf der Basis der pain.001.001.02 ist nur die
             Grouping Option Grouped mit genau einer Einzeltransaktion
             CreditTransferTransactionInformation >CdtTrfTxInf< zugelassen.

            Belegungsrichtlinien
            Kontoverbindung international IBAN und BIC muessen der IBAN in
            DebtorAccount bzw. der BIC in DebtorAgent entsprechen.
            SEPA pain message: Erlaubtes SEPA-Ueberweisungg-Kunde-Bank-Schema lt HISPAS.
            In das Mussfeld RequestedExecutionDate ist der Termin einzustellen.

        Financial Transaction Services (FinTS)
        Dokument: Messages - Multibankfaehige Geschaeftsvorfaelle
        Kapitel: Geschaeftsvorfaelle
        Abschnitt: Einzelueberweisung
        """
        hkcse = HKCSE1
        message += hkcse(
            account=hkcse._fields['account'].type.from_sepa_account(
                _sepaaccount(bank)),
            sepa_descriptor=bank.sepa_descriptor,
            sepa_pain_message=bank.sepa_credit_transfer_data,
        )
        return message

    def segHKVPP(self, message):
        """
        Segment Namensabgleich Pruefauftrag

            Dieser Geschaeftsvorfall wird parallel mit dem Zahlungsverkehrsauftrag, fuer den ein
            Namensabgleich (VOP-Pruefung) durchgefuehrt werden muss, an das Kreditinstitut geschickt.
            Das Kreditinstitut fuehrt den Namensabgleich durch und liefert das Ergebnis
            zurueck.

        Financial Transaction Services (FinTS)
        Dokument: Verification of Payee
        Kapitel: SEPA-Zahlungsverkehr
        Abschnitt: Namensabgleich (Verification of Payee)
        """
        message += HKVPP()
        return message

    def segHNSHA(self, bank, message):
        """
        Segment Signaturabschluss (PIN)

            Der Signaturabschluss stellt die Verbindung mit dem dazugehoerigen Signaturkopf her und
            enthaelt als Validierungsresultat die elektronische Signatur.

        Financial Transaction Services (FinTS)
        Dokument: Security - Sicherheitsverfahren HBCI
        Kapitel: Verfahrensbeschreibung
        Abschnitt: Formate fuer Signatur und Verschluesselung
        """
        if bank.system_id == SynchronizationMode.NEW_SYSTEM_ID:
            message += HKSYN3(SynchronizationMode.NEW_SYSTEM_ID)
        message += HNSHA2(
            security_reference=bank.security_reference,
            user_defined_signature=UserDefinedSignature(PNS[bank.bank_code])
        )
        return message

    def segHNSHA_TAN(self, bank, message):
        """
        Segment Signaturabschluss (PIN/TAN)

            Der Signaturabschluss stellt die Verbindung mit dem dazugehoerigen Signaturkopf her und
            enthaelt als Validierungsresultat die elektronische Signatur.

        Financial Transaction Services (FinTS)
        Dokument: Security - Sicherheitsverfahren HBCI
        Kapitel: Verfahrensbeschreibung
        Abschnitt: Formate fuer Signatur und Verschluesselung
        """
        if bank.system_id == SynchronizationMode.NEW_SYSTEM_ID:
            message += HKSYN3(SynchronizationMode.NEW_SYSTEM_ID)
        if bank.tan_process != 'S':
            if bank.bank_code == '76030080' and bank.challenge_hhduc:  # Consors  Show QR_Code
                challenge_text = bank.challenge + '/n/n' + MESSAGE_TEXT['BANK_CONSORS_TRANSFER']
                MessageBoxInfo(MESSAGE_TEXT['BANK_CHALLENGE'].format(
                    bank.bank_name, bank.bank_code, bank.account_number, bank.account_product_name, challenge_text), bank=bank)
                self._show_tan_qr_code(bank.challenge_hhduc)
            # tan decoupled
            input_tan = InputTAN(bank.bank_code, bank.bank_name)
            if input_tan.button_state == WM_DELETE_WINDOW:
                return None
            message += HNSHA2(
                security_reference=bank.security_reference,
                user_defined_signature=UserDefinedSignature(
                    PNS[bank.bank_code], input_tan.tan),
            )
        else:
            message += HNSHA2(
                security_reference=bank.security_reference,
                user_defined_signature=UserDefinedSignature(PNS[bank.bank_code])
                )
        return message

    def _show_tan_qr_code(self, challenge_hhduc):
        """
        Show TAN QR_Code
        """
        # challenge_hhduc contains binary data, but with header ("\\x00\\timage/png\\x020")
        data = challenge_hhduc
        # Cut off header: everything up to the first PNG header (b"\x89PNG")
        png_start = data.find(b"\x89PNG")
        if png_start == -1:
            raise ValueError(MESSAGE_TEXT('VOP_HHDUC'))
        png_bytes = data[png_start:]  # pure PNG image
        image = Image.open(BytesIO(png_bytes))
        image.show()  # opens QR code with standard viewer

    def segHNHBS(self, bank, message):
        """
        Segment Nachrichtenabschluss
        
            Dieses Segment beendet alle Kunden- und Kreditinstitutsnachrichten.

        Financial Transaction Services (FinTS) 3.0
        Dokument: Formals
        Kapitel: Nachrichtenaufbau
        Abschnitt: Steuerstrukturen
        """
        message += HNHBS1(message.segments[0].message_number)
        encrypt(bank, message)
        message.segments[0].message_size = len(message.render_bytes())
        bank.message_number += 1
        return message

    def segHNHBSnoencrypt(self, bank, message):
        """
        Segment Nachrichtenabschluss

            Dieses Segment beendet alle Kunden- und Kreditinstitutsnachrichten
            ohne Verschluesselung

        Financial Transaction Services (FinTS) 3.0
        Dokument: Formals
        Kapitel: Nachrichtenaufbau
        Abschnitt: Steuerstrukturen
        """
        message += HNHBS1(message.segments[0].message_number)
        message.segments[0].message_size = len(message.render_bytes())
        bank.message_number += 1
        return message

    def segHKEND(self, bank, message):
        """
        Segment Dialogende

            Die Nachricht muss signiert und verschluesselt werden (Ausnahmen s. Kap. C.4.1)
            und wird mit einer Standard-Kreditinstitutsnachricht beantwortet.
            Die Nachricht ist von demjenigen Benutzer zu signieren, der auch die
            Dialoginitialisierung signiert hat.

        Financial Transaction Services (FinTS) 3.0
        Dokument: Formals
        Kapitel: Dialogspezifikation
        Abschnitt: Dialogbeendigung
        """
        message += HKEND1(bank.dialog_id)
        return message
