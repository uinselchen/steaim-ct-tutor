"""Build the source-grounded German YAML inventory without importing the app."""
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from html.parser import HTMLParser

sys.path.insert(0, str(Path(os.environ['TEMP']) / 'steaimct-yaml-doc-tools'))
import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'tutor_funktionalitaet_und_struktur.yaml'


class Dumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True


def represent_text(dumper, value):
    return dumper.represent_scalar('tag:yaml.org,2002:str', value, style='|' if '\n' in value else None)


Dumper.add_representer(str, represent_text)


def read(relative):
    return (ROOT / relative).read_text(encoding='utf-8-sig')


def lines(text):
    return [x.strip() for x in text.strip().splitlines() if x.strip()]


def record(wann, bedingung, aktion, danach=None):
    result = dict(wann=wann, bedingung=bedingung, aktion=aktion)
    if danach is not None:
        result['danach'] = danach
    return result


def element(id, funktion, entscheidung):
    return dict(element=id, funktion=funktion, entscheidung_oder_verhalten=entscheidung)


PURPOSE = {}


def purposes(text):
    for entry in lines(text):
        key, value = entry.split('|', 1)
        PURPOSE[key.strip()] = value.strip()


purposes('''
ensure_directories|Legt benötigte Anwendungsordner und eine leere Schlüsseldatei an, falls sie fehlen.
_reset_config_values|Setzt Konfiguration vor erneutem Laden auf definierte Standardwerte zurück.
_read_local_api_key|Liest nur den lokalen API-Schlüssel; liefert bei fehlender/unlesbarer Datei None.
_apply_env_value|Übernimmt unterstützte Konfigurationswerte, konvertiert SMTP-Port und boolesche Optionen.
_load_env_file_values|Liest lokale .env; übernimmt Schlüssel nur, wenn noch keiner gesetzt ist.
_load_process_environment_values|Übernimmt Prozessvariablen; ein bereits lokal gefundener Schlüssel bleibt vorrangig.
load_env_file|Lädt Standards, Schlüsseldatei, .env und Prozessvariablen in definierter Reihenfolge.
parse_bool_value|Erkennt 1, true, yes und on als wahr; bei None gilt der übergebene Standard.
parse_subjects_value|Akzeptiert Liste, JSON oder durch Semikolon/Komma getrennten Text; entfernt leere Werte und Duplikate.
build_conversation_text|Formatiert Nachrichten mit Rolle, optionaler Zeit und Text als Gesprächsprotokoll.
redact_secrets|Ersetzt bekannte API-Schlüssel und erkannte Bearer-/MISTRAL_API_KEY-Muster in Logtexten.
ensure_log_files|Legt Analyse- und Prompt-Logdateien durch Öffnen im Append-Modus an.
_console_message|Passt Konsolentext an deklarierte Windows-Streamcodierung an; bei Encodingfehler UTF-8-Buffer-Fallback.
log_message|Schreibt redigierte Meldung auf Konsole und in analysis-log.txt.
log_mistral_prompt|Protokolliert Zeit, Label, vollständigen System-/User-Prompt und Request-Body nach Schlüsselredaktion.
load_prompt_file|Lädt eine externe Promptdatei für den aktuellen Aufruf; fehlende Datei wird geloggt und als Fehler weitergegeben.
slugify_folder_name|Normalisiert Land/Fach für Ordnernamen: ASCII, Kleinbuchstaben, Bindestriche; Fallback unknown.
ensure_step2_folder_structure|Erstellt Lehrplan- und Änderungsordner nach Land und Fach und gibt deren Pfade zurück.
save_uploaded_files_to_folder|Speichert Zusatzdateien und verhindert Namenskollisionen durch nummerierte Suffixe.
step3_state_path|Berechnet den JSON-Zustandspfad für eine Sitzung; ohne ID leerer Pfad.
step3_conversation_log_path|Berechnet den TXT-Gesprächspfad für eine Sitzung.
save_step3_state|Speichert serverseitigen Sitzungs-Snapshot als UTF-8-JSON und meldet Schreibfehler.
load_step3_state|Lädt gespeicherten Snapshot; bei fehlender Datei oder Lesefehler None.
save_step3_conversation_log|Speichert Memory-Zusammenfassung und vollständiges Gespräch als TXT.
relative_path|Stellt einen Pfad relativ zum app-Ordner dar; bei inkompatiblen Laufwerken absolut.
read_env_values|Liest .env-Schlüssel/Werte, ignoriert Kommentare und Leerzeilen.
write_env_values|Aktualisiert einzelne .env-Werte und bewahrt unbetroffene Zeilen/Kommentare.
write_mistral_api_key|Schreibt den eingegebenen Schlüssel in die lokale Schlüsseldatei.
build_settings_status|Ermittelt KI-, Ordner-, Prompt-, Python- und Exportabhängigkeitsstatus ohne den Schlüsselwert auszugeben.
update_mistral_settings|Speichert nicht leere API-/Modellwerte und optional neuen Schlüssel, lädt Konfiguration neu.
extract_text_from_file|Verteilt Dateiformate auf TXT/MD/CSV-Lesen, PDF- oder DOCX-Extraktion; unbekanntes Format liefert leeren Text.
extract_text_from_pdf|Extrahiert Text seitenweise mit pypdf; keine OCR; einzelne Seitenfehler werden toleriert.
extract_text_from_docx|Liest word/document.xml aus dem DOCX-ZIP und verbindet Texte der Absätze.
normalize_computational_thinking|Liefert genau sechs CT-Einträge in fester Reihenfolge; ungültige Status werden Not identified.
get_step3_focus_label|Verbindet Label, Punkt-Titel und ID des aktiven Fokus für Memory-Kontext.
summarize_step3_changes|Beschreibt die letzten acht Änderungen mit Vorher/Nachher und Begründung.
build_step3_memory_summary|Baut Sitzung, Land/Fächer, Fokus, letzte Eingabe, acht Änderungen und zehn Nachrichten als Gedächtnis auf.
extract_json_block|Entfernt mögliche Codefences bzw. extrahiert ein JSON-Objekt aus der Modellantwort.
repair_json_quotes|Versucht problematische Anführungszeichen im Modell-JSON lokal zu reparieren.
repair_json_common_mistakes|Repariert typische JSON-Syntaxprobleme lokal.
parse_json_response_block|Extrahiert und parst JSON mit lokalen Reparaturversuchen; protokolliert Fehlerkontext.
build_mistral_request_body|Erstellt System-/User-Nachrichten mit Modell, Temperatur 0.2 und JSON-Object-Ausgabeformat.
post_mistral_chat_completion|Sendet JSON per urllib an konfigurierte API mit Bearer-Header und aufrufabhängigem Timeout.
repair_mistral_json_with_model|Fordert bei lokal nicht reparierbarem JSON einmal eine Modellreparatur an.
parse_mistral_json_content|Prüft auf JSON-Objekt, versucht lokale und bei Parsefehler Modellreparatur, liefert sonst Fehlerobjekt.
maybe_retry_without_response_format|Wiederholt Anfrage ohne response_format und stellt anschließend den Request-Parameter wieder her.
format_context_range|Formatiert einen Von-/Bis-Bereich bzw. einen Unbekannt-Hinweis.
build_ui_target_context|Baut normalisierten, vorrangigen Kontext aus Land, Fächern, Stufe, Alter, Besonderheiten und Sprache.
build_analysis_context_summary|Stellt Lehrkraftkontext und Sprach-/Fachpriorität vor den vollständigen Analyse-Payload.
call_mistral_analysis|Lädt Analyseprompt, sendet Kontext, behandelt API-/JSON-Fehler und normalisiert CT-Ergebnisse.
call_mistral_analysis_discussion|Sendet genau einen Analysepunkt samt Dialogkontext und normalisiert die Diskussionsantwort.
call_mistral_refinement|Lädt Refinementprompt, stellt Memory vor Roh-Payload und fordert strukturiertes Entwurfsupdate an.
call_mistral_hello|Testet KI mit Say hello bei Temperatur 0; nutzt fest codierte offizielle Mistral-URL.
do_GET|Verteilt GET-Anfragen auf Startseite, Ping, Zustand, Konfiguration, Status und statische Dateien.
do_POST|Verteilt POST-Anfragen auf Upload, Analyse, Diskussion, Vorbereitung, Refinement, Export, Logs und Einstellungen.
handle_upload|Optionaler Upload-Endpunkt: speichert Original und gegebenenfalls Besonderheiten-TXT; löst keine Analyse aus.
handle_analyze|Liest Multipart-Upload, extrahiert Text, speichert Original, erzeugt Kontext und ruft erste KI-Analyse auf.
handle_step2_prepare|Speichert Zusatzdateien und Metadaten, erzeugt Sitzung und Land-/Fachordner für den Übergang zu Schritt 3.
handle_export_docx|Baut DOCX/PDF-Bundle und liefert die DOCX-Datei als HTTP-Download.
handle_export_pdf|Baut DOCX/PDF-Bundle und liefert die PDF-Datei als HTTP-Download.
handle_analysis_discuss|Validiert JSON-Anfrage, ruft Punktdiskussion auf und liefert 200 oder 502.
handle_export_analysis_docx|Erzeugt DOCX-Bericht mit Analyse, Diskussionen und Klärungen und liefert ihn aus.
handle_step3_refine|Ruft Refinement auf und speichert dessen Roh-Ergebnis, Entwurf, Gespräch, Fortschritt und Payload serverseitig.
handle_step3_state|Lädt Sitzungszustand per Query sessionId; fehlende ID 400, unbekannte Sitzung 404.
handle_send_email|Optionaler Backend-Aufruf zum Versand von Änderungs-/Pro-/Contra-TXT-Anhängen.
handle_mistral_test|Ruft Hello-Test auf und liefert dessen Erfolg oder Fehler als JSON.
handle_client_log|Schreibt übermittelten Client-Logtext in das lokale Analyseprotokoll.
serve_config|Liefert Länder- und Fächerkonfiguration aus config.json.
serve_settings_status|Liefert System- und Konfigurationsstatus ohne geheime Schlüsselwerte.
handle_settings_update|Validiert JSON und speichert Mistral-Einstellungen über settings_service.
handle_config_update|Ergänzt neue Länder/Fächer ohne Duplikate in config.json.
serve_path|Normalisiert angefragte statische Pfade, lehnt .. und Verzeichnislisten ab, liefert existierende Dateien.
serve_file|Liefert Dateiinhalt mit Content-Type und Content-Length; bei Lesefehler 404.
guess_type|Ermittelt MIME-Typ für unterstützte Frontend- und Dokumentdateien.
run_server|Wechselt in app, startet HTTPServer auf Port 8000, öffnet Browser und verarbeitet Anfragen fortlaufend.
normalize_filename_piece|Erzeugt begrenzte ASCII-Dateinamen mit Bindestrichen und Fallback.
normalize_text_list|Bereinigt Listen auf nicht leere Textwerte.
normalize_source_document|Normalisiert verschiedene Originaldatei-Feldnamen auf path/filename/storedFilename.
find_uploaded_file_path|Sucht Upload zuerst direkt, dann rekursiv; bei mehreren Treffern gilt neuester Änderungszeitpunkt.
resolve_source_document|Findet Originaldatei über Payload-/Snapshot-Pfade oder mehrere Dateiname-Aliasse.
build_export_context|Lädt Snapshot, priorisiert Serverentwurf vor Requestentwurf und extrahiert Originaltext für Export.
collect_export_changes|Normalisiert Änderungen aus Entwurf, Ergebnis oder Payload mit Ort und Vorher/Nachher.
get_final_plan_context|Stellt sämtliche finalen Planfelder, Gespräch, Änderungen und Originaltext für Renderer zusammen.
build_export_metadata_lines|Formatiert Land, Fächer, Stufen und Alter als Export-Metadaten.
normalize_heading_key|Normalisiert Überschriften für Abschnittserkennung und Zuordnung.
split_text_to_paragraphs|Zerlegt Originaltext in bereinigte Absatzzeilen.
replace_first_non_empty_line|Ersetzt erste befüllte Zeile durch aktuellen Titel.
replace_metadata_lines|Ersetzt vorhandene Metadatenzeilen bzw. ergänzt aktuelle Metadaten.
apply_inline_replacements|Wendet aufgezeichnete skalare Vorher-/Nachher-Ersetzungen auf Textzeilen an.
replace_section_block|Ersetzt oder ergänzt benannten Abschnitt bis zur nächsten bekannten Überschrift.
build_final_export_lines|Baut textbasierten finalen Plan aus Originaltext, Ersetzungen und strukturierten Entwurfsabschnitten.
can_use_source_docx_template|Prüft Verfügbarkeit von python-docx und einer vorhandenen DOCX-Originaldatei.
add_docx_bullet_paragraph|Erzeugt Aufzählungsabsatz, optional fett, mit Stil-Fallback.
add_docx_bullet_list|Erzeugt mehrere DOCX-Aufzählungsabsätze.
add_docx_text_section|Fügt DOCX-Überschrift und Textzeilen ein.
iter_docx_paragraphs|Iteriert Absätze im Dokument und in Tabellenzellen.
change_replacements|Leitet Ersetzungspaare aus Skalar-, Listen- oder Schrittobjekt-Änderungen ab.
replace_in_docx_paragraph|Ersetzt zuerst in Runs; Absatz-Fallback nur ohne Zeichnungen, mit möglichem Verlust der Run-Formatierung.
change_location_key|Bestimmt normalisierten Abschnittsschlüssel einer Änderung.
paragraphs_for_change|Begrenzt Ersetzung auf passende Überschrift/Schritt bis zur nächsten Abschnittsgrenze.
apply_tutor_changes_to_docx|Ersetzt lokalisierbare Änderungen im Original; globaler Fallback nur bei eindeutigem Texttreffer.
render_source_docx_with_changes|Öffnet Original-DOCX, wendet aufgezeichnete Änderungen an und speichert neue Datei.
render_lines_to_docx|Erzeugt textbasiertes DOCX mit Titel, Überschriften, Absätzen und Aufzählungen.
build_analysis_docx|Erzeugt strukturierten Analysebericht einschließlich CT, Diskussionen und Klärungen.
format_export_range|Formatiert erkannten Stufen-/Altersbereich für Bericht.
render_lines_to_pdf|Erzeugt A4-PDF mit ReportLab, Helvetica, eigenen Text-/Überschriftsstilen und XML-Escaping.
ensure_export_folder|Erzeugt normalisierten Exportordner pro Sitzung.
build_docx_export|Verwendet Original-DOCX als Vorlage; bei Fehlschlag textbasierter Fallback.
build_pdf_export|Rendert textbasierten finalen Plan als PDF.
build_export_bundle|Erzeugt und validiert bei jedem Aufruf sowohl DOCX als auch PDF im Sitzungsordner.
validate_export_file|Prüft Existenz, Dateigröße und PDF-Magic bzw. DOCX-ZIP-Struktur.
normalize_email_list|Normalisiert Empfängerlisten aus Liste oder Komma-/Semikolontext ohne Duplikate.
build_change_steps_text|Erstellt ausschließlich Änderungspakettext für optionalen E-Mail-Anhang.
build_analysis_points_text|Formatiert verfügbare strengths/issues als Pro-/Contra-Text.
send_summary_email|Versendet drei TXT-Anhänge über konfiguriertes SMTP mit optional SSL/TLS/Login.
tr|Übersetzt UI-Text über tutorTranslate; falls nicht verfügbar bleibt Ausgangstext.
uiText|Übersetzt UI-Text mit Ausgangstext als Fallback.
safeParse|Parst Browser-JSON mit lokalem Fallback statt einer ungefangenen Exception.
normalizeItems|Normalisiert Listen/Textwerte für UI-Darstellung.
setText|Schreibt Text in bestimmtes DOM-Element; im Settings-Kontext zusätzlich Statusklasse.
formatRange|Formatiert Von-/Bis-Bereich für UI.
formatTextList|Verbindet Textliste für Anzeige.
getTimeStamp|Erzeugt sichtbaren Zeitstempel im Browser.
clone|Erzeugt JSON-basierte tiefe Kopie von UI-Zustand/Daten.
languageForCountry|Ordnet Land einer Sprache zu; unbekanntes Land wird selbst zum Sprachnamen.
loadLanguageCountries|Lädt Länder für Sprachwahl aus /config mit English-Default und Fehlerfallback.
setApiKeyModalOpen|Schaltet Setup-Modal und aria-hidden.
loadApiKeyStatus|Lädt /settings-status und ermittelt API-Konfiguration sowie Startbereitschaft.
showSetupRequired|Zeigt fehlenden Schlüssel, Pakete, Ordner oder nicht verfügbaren Setup-Status im Modal.
clearLessonSessionState|Entfernt vorhandene Analyse-, Diskussions- und Refinement-Browserdaten vor neuem Upload.
setAnalyzingState|Sperrt Continue während Analyse und zeigt Ladezustand/Analyzing.
setError|Zeigt Feldfehler und markiert passende Überschrift/Label.
clearError|Entfernt Meldung und zugehörige Fehlermarkierung.
setErrorDetail|Zeigt technische Details oder rohe Fehlerantwort unter dem Uploadfeld.
updateFileDisplay|Zeigt ersten ausgewählten Dateinamen und auf KB gerundete Größe.
toggleCountryOther|Blendet freies Landfeld und Hinzufügen-Button bei Other ein; löscht sonst Freitext.
updateAddCountryButton|Zeigt Länder-Hinzufügen nur bei Other und nicht leerer Eingabe.
toggleSubjectOther|Blendet freies Fachfeld und Hinzufügen-Button abhängig von Other-Checkbox ein.
updateAddSubjectButton|Zeigt Fach-Hinzufügen nur bei aktivem Other und nicht leerem Freitext; zweimal gleich definiert.
getSelectedSubjects|Liest aktivierte Fachcheckboxen und ersetzt Other durch eingegebenes Fach.
normalizeNumericText|Verbindet sämtliche Zifferngruppen; keine pädagogische Bereichsprüfung.
handleNumericInput|Entfernt nicht numerische Zeichen und gibt bei Änderung einen Browserhinweis aus.
showInputGuidance|Zeigt feldbezogene Hinweise für Stufe oder Alter.
populateSelect|Baut Länderoptionen einschließlich Other neu auf.
populateSubjects|Baut Fachcheckboxen einschließlich Other und zugehörigen Eventhandlern neu auf.
loadConfig|Lädt Länder/Fächer; bei Netzwerkfehler fest definierte Auswahllisten.
saveCustomSubject|Sendet neues Fach per JSON an POST /config.
saveCustomCountry|Sendet neues Land per JSON an POST /config.
validateForm|Prüft Pflichtangaben, Bereiche, Dateiendung und clientseitig maximal 20 MiB.
uploadForm|Löscht alte Sitzung, speichert neue Auswahlwerte, testet KI und startet Analyse mit Multipart-FormData.
sendClientLog|Sendet Diagnosemeldung an /client-log; Fehler beeinträchtigt Arbeitsablauf nicht.
runMistralHello|Fordert KI-Verbindungstest an; Fehlschlag verhindert anschließende Analyse.
renderAnalysisError|Zeigt fehlende/fehlerhafte Analyse und optional Rohantwort statt Analyseinhalt.
openCitationModal|Zeigt gelieferte Belegstelle mit Kontext im Modal.
closeCitationModal|Schließt Belegstellen-Modal.
getFallbackCategories|Baut bekannte Kategorien aus verfügbaren älteren Analysefeldern, wenn categories fehlen.
getCategoryDefaults|Ordnet Kategorien Standardtitel, Beschreibung und Akzentfarbe zu.
normalizeCategory|Ergänzt fehlende Kategorieanzeigefelder aus Standardwerten.
loadPointDiscussions|Lädt lokal gespeicherte Punktdialoge oder leeres Objekt.
savePointDiscussions|Persistiert Punktdialoge im Browser.
getPointDiscussionKey|Erzeugt eindeutigen Schlüssel aus Kategorie und Punkt-ID.
renderPointDiscussionMessages|Zeigt Punktdialog und gespeicherte Zusammenfassung.
createPointDiscussion|Erzeugt Nachrichtenfeld, Senden, Entscheidungswahl und Include-in-download für einen Analysepunkt.
sendMessage|Speichert Lehrkraftnachricht, sendet Punktdialog an API, übernimmt Antwort/Entscheidung/Adaptation oder zeigt Fehler.
renderCategory|Rendert Kategorie mit höchstens acht Punkten als sechsspaltige Tabelle und Punktdialogen.
collectSelections|Übernimmt markierte Punkte sowie Punkte mit Gespräch; Kommentar aus Zusammenfassung/letzter Lehrkraftnachricht.
normalizeMatchWords|Normalisiert Status-/Hinweistext für lexikalische Farbzuordnung.
containsMatchWord|Prüft, ob Text einen definierten Farbmarker enthält.
getWordScoreClass|Ermittelt Rot/Gelb/Grün anhand Markerlisten, wenn kein numerischer Score vorliegt.
isCriticalText|Prüft auf rote Statusmarker.
normalizeMatchScore|Wandelt numerische Werte um, rundet und begrenzt auf 1 bis 10; fehlend/ungültig null.
getScoreClass|Ordnet Match 1–3 Rot, 4–6 Gelb und 7–10 Grün zu.
formatStatusLabel|Ersetzt Unterstriche durch Leerzeichen; Fallback unclear.
getPrivacyWarningText|Sucht Privacy-Marker in Analysehinweisen und unterdrückt einige generische Platzhalterwarnungen.
openPrivacyModal|Zeigt personenbezogenen Hinweis im Modal.
closePrivacyModal|Schließt Privacy-Modal nur nach bestätigten Beispieldaten oder erzwungenem Schließen.
collectSelectionsForNextStep|Ergänzt Punktwahl um nicht leere CT-Klärungen und vorrangigen Privacy-Punkt.
renderSummary|Zeigt Zusammenfassung, Erkennungen, Sicherheit und Hinweise.
renderAnalysisFocus|Erzeugt sechs Übersichtskarten mit Status, Match, Sicherheit, Begründung und Farbfallback.
normalizeComputationalThinkingForDisplay|Ergänzt fehlende CT-Zeilen und normalisiert Status/Detailtext für UI.
appendCtDetail|Fügt beschriftete CT-Detailzeile mit sicherer Textausgabe ein.
renderComputationalThinking|Rendert sechs aufklappbare CT-Zeilen; Klärungs-Textarea ausschließlich bei Not identified.
renderMeta|Zeigt Kontextmetadaten des aktuellen Unterrichts in Analyse bzw. Download.
buildAnalysisDownloadText|Formatiert ausführlichen Analyse-Text; aktive Download-Schaltfläche verwendet DOCX-Endpunkt.
downloadAnalysisDocx|Sendet Analyse/Metadaten/Dialoge/Klärungen an DOCX-Export und lädt Blob herunter.
getAdditionalUploadState|Liest gespeicherte Zusatzdateimetadaten; keine Wiederherstellung der File-Objekte.
setAdditionalUploadState|Speichert Name, Größe und MIME-Typ der Zusatzdateien im Browser.
renderAdditionalUploadList|Zeigt ausgewählte Zusatzdateien oder Leermeldung.
updateAdditionalUploadFromInput|Ersetzt aktuelle File-Liste und aktualisiert Metadaten/Anzeige.
getCountryLabel|Nimmt Land aus Uploadmetadaten, sonst Vorbereitung, sonst Unknown country.
getSubjectLabels|Nimmt Fächer aus Uploadmetadaten, sonst Vorbereitung.
buildBaseDraft|Erzeugt festen Basisentwurf mit sechs generischen Schritten und insgesamt 90 Minuten; kein Originalplanparser.
ensureDraft|Stellt Entwurf und changes-Liste sicher; ohne Entwurf wird feste Vorlage erstellt.
persistState|Speichert Entwurf, Gespräch, Tab, Themenindex, Freitextstatus und Sitzungs-ID lokal.
addConversation|Ergänzt Nachricht mit Rolle, Zeit und aktivem Thema, persistiert und rendert Gespräch.
addChange|Ergänzt Änderung mit Vorher/Nachher, Grund, Quelle und Zeit; persistiert und rendert Vorschau.
stringifyComparable|Serialisiert Werte für Vergleich.
valuesDiffer|Vergleicht JSON-Repräsentationen zweier Werte.
formatHistoryValue|Wandelt strukturierte Werte in lesbare Änderungsbeschreibung um.
formatChangeDetails|Baut Vorher-/Nachher-Detailtext für Änderung.
formatHistoryTitle|Wählt lesbaren Titel für Änderung.
formatHistoryLocation|Bestimmt angezeigte Dokumentstelle aus Änderungseintrag.
normalizeChangeSection|Ordnet Änderung anhand Feldern/Textmarkern einem Vorschauabschnitt zu.
getChangedSections|Ermittelt geänderte Abschnitte aus Änderungshistorie.
changeAlreadyExists|Verhindert doppelte generierte Änderungsmarker.
pushGeneratedChange|Ergänzt automatisch festgestellte Änderung mit Abschnitt und Vorher/Nachher.
ensureVisibleDraftChanges|Vergleicht alten/neuen Entwurf und ergänzt fehlende Änderungsmarker für Felder und Schritte.
isGenericPrivacyFalsePositive|Filtert einige generische personenbezogene Warnungen vor Themenbildung.
buildConversationNodes|Baut priorisierte Themen aus Auswahl; bekannte Kategorien zuerst, dann Fallbacks; dedupliziert pro Kategorie.
getRepliesForCategory|Liefert fest definierte Ausgangsantworten für sechs Kategorien oder generische Fallbacks.
isKeepAsIsReply|Erkennt bestimmte englische Beibehalten-/Überspringen-Antworten per Regex.
continueWithoutChangingTopic|Bearbeitet Beibehalten lokal ohne API, ergänzt Gespräch und wechselt zum nächsten Thema.
applyConversationReply|Lokale regelbasierte Demo-Änderungslogik; im aktiven submitReply-Ablauf nicht aufgerufen.
renderFocusStrip|Erzeugt anklickbare Themenchips mit aktivem Marker.
jumpToTopic|Wechselt Thema, persistiert Fortschritt und scrollt zu bestehendem Gespräch oder erzeugt Einleitung.
renderRefinementOverview|Berechnet Index-basierten Fortschritt und zeigt aktives/nächstes Thema sowie letzte Änderung.
renderConversation|Rendert Nachrichten in zusammenhängenden Themengruppen mit Rolle/Zeit und scrollt nach unten.
renderQuickReplies|Erzeugt Antwortbuttons aus Modelloptionen oder Themenstandards; Klick sendet sofort.
buildPreviewTabs|Definiert sechs Tabs: Goals, Skills, Steps, Materials, Assessment, Reflection.
renderPreviewTabs|Erzeugt Tabs, markiert aktive/geänderte Abschnitte; Wechsel persistiert und rendert Vorschau.
renderSectionContent|Rendert Metadaten und ausgewählten Entwurfsabschnitt inklusive Änderungsmarkierung.
sectionCard|Lokaler Helfer für Vorschaukarten mit Titel, Status, Notiz und Inhalt.
renderChangeSummary|Zeigt Anzahl und jüngste Änderungen in der Refinement-Vorschau.
renderPreview|Aktualisiert Entwurfstitel, Tabs, Inhalt und Änderungszusammenfassung.
renderHistoryModal|Rendert vollständige Änderungshistorie im gemeinsamen Modal.
openHistoryModal|Füllt und öffnet Änderungs-Modal.
closeHistoryModal|Schließt Änderungs-/Stärken-Modal.
exportDraft|Lädt lokalen TXT-Zwischenstand als lesson-plan-draft.txt herunter; kein API-Aufruf.
setReplyBusy|Sperrt Eingabe, Senden und Quick Replies; zeigt Thinking und aria-busy.
buildQuickReplyPrompt|Erweitert Zeitantworten um Scope-Regeln sowie Wording-/Alternativanfragen um präzise Arbeitsaufträge.
isSuggestWordingRequest|Erkennt englisches suggest wording in einer Nachricht.
isExplicitSectionUpdateRequest|Erkennt englische Bearbeitungsverben und benannte Entwurfsabschnitte.
isEmptyWordingMessage|Erkennt leere/nur Überschrift oder unter fünf Wörter lange Formulierungsausgabe.
hasRelevantWordingDraftChange|Prüft, ob zur Formulierungsanfrage passendes Entwurfsfeld tatsächlich geändert wurde.
isIncompleteWordingResponse|Meldet Antwort als unvollständig, wenn weder konkrete Formulierung noch relevantes Update vorliegt.
buildScopedUserMessage|Ergänzt Nachricht um Zeit-Scope oder Aufforderung, explizite Abschnittsänderung wirklich im JSON anzuwenden.
durationMinutes|Erkennt Zahlen mit min sowie NxM min, Komma wird Dezimalpunkt; unbekanntes Format 0.
draftDurationTotal|Summiert erkannte Schrittminuten.
extractAdditionalMinutes|Extrahiert englisch beschriebene Minuten; Fallback beliebige Zahl vor minutes.
applyClaimedAdditionalTime|Ergänzt behauptete Mehrzeit ohne echte Daueränderung am dritten bzw. letzten Schritt.
timingAssessmentIsTight|Prüft aktiven Themenkontext auf einige englische Marker für knappe Zeit.
hasReducedStepDuration|Prüft indexweise, ob ein Schritt kürzer geworden ist.
applyExplicitSplitChoice|Erkennt A+B, verteilt A auf erste zwei Schritte im Verhältnis 43/57, B auf übrige Schritte.
buildRefinementPayload|Sendet Sitzung, Kontext, Auswahl, Analysefelder, aktiven Knoten, Fortschritt, Entwurf und vollständiges Gespräch.
constrainUpdatedDraft|Begrenzt Zeit-Fokus clientseitig auf Dauer/Status/Notizen, verhindert Gesamtkürzung und filtert Änderungen.
applyUpdatedDraft|Führt akzeptierte Felder in Entwurf zusammen; leere Listen ersetzen bestehende Listen nicht.
requestRefinementFromMistral|POST /step3-refine mit JSON und Fehlerauswertung.
loadPersistedStep3State|Versucht Serverzustand zu laden; fehlende Sitzung/Fehler wird als null toleriert.
applyLoadedStep3State|Übernimmt Serverentwurf, Gespräch und Fortschritt vor Bootstrap.
submitReply|Steuert aktiven Dialog: lokale Keep-Antwort, KI-Anfrage, Wording-/Zeitprüfungen, Draft-Update und Themenwechsel.
startNextNode|Aktiviert nächstes Thema und zeigt lokale Einleitung/Antwortbuttons; nach letztem Thema bleibt Freitext offen.
resetConversation|Löscht sichtbares Gespräch und Themenfortschritt, behält Entwurf/Änderungen und startet Fragen neu.
bootstrap|Baut Basiszustand, Themen und UI; startet lokales Begrüßungsgespräch oder setzt vorhandenes fort.
init|Lädt zuerst optional Serverzustand und startet dann Bootstrap.
makeParagraph|Erstellt Textabsatz für Downloadvorschau.
getDraft|Liest step3Draft aus localStorage.
getConversationLog|Liest step3Conversation aus localStorage.
getPreparation|Liest step2Preparation aus localStorage.
setBusyState|Helfer zum gemeinsamen Sperren von Abschluss-/Exportbuttons; nicht vom aktiven exportFile verwendet.
buildConversationText|Formatiert Gespräch im Frontend als Text.
buildPreview|Rendert sechs finale Entwurfsabschnitte einschließlich Schrittstatus und Notizen.
renderChangeList|Zeigt Anzahl und erste sechs Änderungen in der Download-Seitenleiste.
renderStrengths|Zeigt erste fünf Einträge der festen Stärkenliste.
getInitialStrengths|Liefert fünf fest codierte Stärken; liest keine tatsächlichen Analyseergebnisse.
triggerDownload|Lädt Blob über temporären Object-URL/Link herunter und gibt URL später frei.
cleanServerError|Extrahiert verständliche Meldung aus HTML-Serverfehler oder liefert Fallback.
buildExportPayload|Erzeugt Exportanfrage aus Sitzung, Dateiname, lokalem Entwurf, Gespräch und Originaldatei.
exportFile|Fordert DOCX/PDF an, sperrt jeweiligen Button, lädt Blob mit festem Frontend-Dateinamen herunter.
renderStrengthsModal|Füllt gemeinsames Modal mit fest codierter Stärkenliste.
openStrengthsModal|Öffnet Stärkenansicht im gemeinsamen Modal.
copyToClipboard|Kopiert Titel, Zusammenfassung, Ziele und Schritttitel/Dauern; keine vollständige Planübertragung.
finishLessonPlan|Löscht vier Step-3-Browserschlüssel und navigiert zur Startseite; löscht keine Serverdateien.
start|Initialisiert Downloadvorschau, Seitenleisten, Metadaten und Eventhandler.
setInputValue|Füllt Admin-Eingabefeld mit aktuellem Konfigurationswert.
renderPromptPaths|Zeigt gemeldete Promptpfade mit available/missing; kein Prompteditor.
renderRuntimeStatus|Rendert Schlüssel-, Exportpaket-, Ordner- und Pythonprüfung mit Ready/Action required.
applyStatus|Aktualisiert Admin-Statusanzeigen und befüllt API-/Modellfelder; Schlüssel wird nicht vorbefüllt.
loadStatus|Lädt Admin-Status; bei Fehler zeigt Status unavailable.
saveSettings|POST /settings; nach Erfolg Schlüssel-Eingabe leeren und Status aktualisieren.
currentLanguage|Ordnet gespeicherten Sprachnamen einem der acht UI-Sprachcodes zu, sonst en.
translate|Liefert Übersetzung für Sprache oder englischen Ausgangstext.
applyTranslations|Übersetzt statische Selektoren/Platzhalter und setzt HTML-lang bei Seitenstart/Sprachwechsel.
tutorTranslate|Globale Übersetzungsfunktion mit Meldungstabelle, Selektortabelle und Textfallback.
main|Startet lokale unittest-Discovery, schreibt Ergebnis und beendet sich mit entsprechendem Exit-Code.
write_header|Schreibt Startzeit, Python, Plattform, Arbeitsverzeichnis und Logpfad in Testprotokoll.
write|Schreibt Testausgaben in die vom Testrunner verwalteten Streams.
flush|Leert die vom Testrunner verwalteten Ausgabestreams.
''')


class DOM(HTMLParser):
    VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.nodes = []
        self.stack = []

    def handle_starttag(self, tag, attrs):
        # Inline code is preserved in the source appendix, not mistaken for UI text.
        node = {'tag': tag, 'zeile': self.getpos()[0], 'attribute': dict(attrs), 'parent_index': self.stack[-1] if self.stack else None, 'textteile': []}
        self.nodes.append(node)
        if tag not in self.VOID:
            self.stack.append(len(self.nodes) - 1)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID and self.stack:
            self.stack.pop()

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.nodes[self.stack[index]]['tag'] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        if self.stack and self.nodes[self.stack[-1]]['tag'] not in ('script', 'style'):
            clean = ' '.join(data.split())
            if clean:
                self.nodes[self.stack[-1]]['textteile'].append(clean)


DOC = {
    'dokument': {
        'titel': 'STEaiM-CT Tutor: vollständige Funktions-, UI-, Ablauf- und Promptinventur',
        'stand': '2026-10-02', 'sprache': 'Deutsch', 'format': 'YAML 1.2, UTF-8',
        'grundlage': 'Statische Bestandsaufnahme des aktuellen Hauptprojekts app/ inklusive Launcher und vorhandener Tests.',
        'ausgeschlossen': ['Separate ältere Kopie tutor1.1/', 'API-Schlüsselwerte und .env-Inhalte', 'Uploadinhalte, Sitzungsdaten und existierende Logs', 'Codex-interne Dateien'],
        'lesereihenfolge': ['produkt', 'architektur', 'seiten', 'ablauf_und_zustandsautomat', 'prompting', 'datenvertraege', 'api', 'persistenz', 'export', 'grenzen_und_abweichungen', 'funktionsinventar', 'ui_und_eventinventar', 'gestaltung', 'quelltextreferenz'],
        'interpretation': {
            'implementiert': 'Im Code vorhanden; keine Aussage, dass alle Pfade im Browser praktisch getestet wurden.',
            'prompt_regel': 'Anweisung an das Sprachmodell; ohne zusätzliche Codeprüfung keine harte Garantie.',
            'code_regel': 'Bedingung oder Verarbeitung, die in Frontend/Backend umgesetzt ist.',
            'produktziel': 'Wunsch der Lehrkraft, nicht automatisch aktuelles Implementierungsverhalten.',
            'vorschlag': 'Besprochene Erweiterung; kein implementiertes Feature.'
        },
        'vollstaendigkeit': 'Jede Quelldatei der definierten Anwendungsauswahl erhält Hash und vollständigen Quelltext. Alle Python-Funktionen und benannten JS-Funktionen, statischen DOM-Knoten, Eventregistrierungen und dynamischen DOM-Erzeugungen werden zusätzlich inventarisiert. Anonyme Callback-Details bleiben vollständig in der Quelltextreferenz erhalten.',
        'keine_nachgewiesene_prompt_optimierung': 'Optimierungen werden als vorhandene Mechanismen und deren beabsichtigter Nutzen beschrieben; keine gemessene Erfolgsquote oder Effizienz behauptet.'
    },
    'produkt': {
        'zielgruppe': 'Lehrkräfte', 'gegenstand': 'Vorhandene Unterrichtspläne reflektieren, kontextbezogen analysieren und verfeinern.',
        'schritte': ['1: Unterrichtskontext und Originalplan', '2: Erste Analyse, Diskussion und Priorisierung', '3: Refinement-Dialog mit Entwurfsvorschau', '4: Ergebnisvorschau und Downloads'],
        'vom_nutzer_klargelegtes_ziel': 'So wenig wie möglich selbst erstellen; konkrete Vorschläge können im Refinement auf Wunsch entstehen.',
        'aktuelles_verhalten': 'Analyse erzeugt bereits Vorschläge. Refinement kann Vorschläge und Entwurfsänderungen direkt liefern und verwendet beim Erststart eine feste generische Entwurfsvorlage.',
        'rollen': {'lehrkraft': 'Kontext, Originalplan, Korrekturen, Fokuswahl und Änderungsentscheidungen.', 'tutor': 'Analyse und Dialog, Formulierungs-/Änderungsvorschläge, strukturierte Updates.', 'frontend': 'Darstellung, Navigation, Zustandsführung und zusätzliche Antwortprüfungen.', 'backend': 'Dateien, KI-Aufrufe, Sitzungs-Snapshots und Dokumentexport.'},
        'optionaler_emailversand': 'Backend vorhanden; keine aktive UI-Steuerung.'
    },
    'architektur': {
        'frontend': {'technologie': 'Statisches HTML/CSS und Vanilla JavaScript; kein Build-/Frameworkschritt.', 'seitenanzahl': 8, 'skripte': 'Start, Lesson-info, Settings und i18n extern; Analyse, Refinement und Download enthalten große Inline-Skripte.'},
        'backend': {'technologie': 'Python http.server.HTTPServer mit TutorHandler; urllib für KI.', 'port': 8000, 'bind': 'Leere Hostadresse: Server bindet grundsätzlich an alle lokalen Interfaces.', 'parallelitaet': 'HTTPServer, kein ThreadingHTTPServer; Serverbearbeitung ist sequenziell.', 'start': 'run_server wechselt nach app/, öffnet localhost im Browser und startet serve_forever.'},
        'module': {
            'app.py': 'HTTP-Routing, Eingabevalidierung und Verbindung der Services.',
            'config.py': 'Pfade, Konstanten, Ordner und Konfigurationspriorität.',
            'config_utils.py': 'Bool-Konvertierung.', 'settings_service.py': 'Status und lokale Einstellungsänderungen.',
            'file_extractors.py': 'Text aus Unterrichtsdokumenten.', 'mistral_service.py': 'Promptaufbau, Requests, Antwortreparatur, CT-Normalisierung.',
            'prompts.py': 'Promptdateien zur Laufzeit laden.', 'step2_service.py': 'Länder-/Fachordner und Zusatzuploads.',
            'step3_service.py': 'JSON-Snapshots und Gesprächs-TXT.', 'export_service.py': 'Originaldateiauflösung, Änderungen, DOCX/PDF/Analyseexport.',
            'email_service.py': 'Optionaler SMTP-Versand.', 'logging_utils.py': 'Logs und Schlüsselredaktion.', 'text_utils.py': 'Fachlisten und Gesprächsformatierung.'
        },
        'konfiguration': {'standardmodell': 'mistral-small-latest', 'standard_api': 'https://api.mistral.ai/v1/chat/completions', 'schluessel_prioritaet': ['Lokale mistral_api_key.txt', '.env, wenn lokal kein Schlüssel gefunden', 'Prozessvariable, wenn weiterhin kein Schlüssel gefunden'], 'andere_werte': 'Standards -> .env -> Prozessvariablen. Nicht leere Prozesswerte überschreiben lokale Konfigurationswerte.', 'timeouts_sekunden': {'analyse': 180, 'punktdiskussion': 180, 'refinement': 120, 'hello': 30, 'modell_json_reparatur': 30}},
        'launcher': {
            'windows': ['Rekursionsschutz über STEAIM_TUTOR_BATCH_ACTIVE.', 'UTF-8-Codepage und Diagnose-TXT im temporären Verzeichnis.', 'Ordner/Logs/Config/.env/Schlüsseldatei prüfen bzw. anlegen.', 'Pflichtdateien prüfen.', 'Python suchen bzw. bereitstellen; Venv und Exportpakete prüfen.', 'Python-3.12.10-Installer-URL ist hinterlegt.', 'Warnung bei fehlendem API-Key oder österreichischer Lehrplandatei.', '--check beendet nach Startprüfung ohne Server.', '--test startet Testlauncher ohne Server.', 'Normalstart öffnet Browser, startet app.py und schreibt server.log.'],
            'shell': ['Projektpfad aus Skriptposition.', 'Benötigte Ordner anlegen.', 'Python3 prüfen, Venv erzeugen, Anforderungen installieren anhand Requirements-Stamp.', 'Schlüsseldatei anlegen; Browser/Server starten.'],
            'macos_command': 'Delegiert per exec /bin/bash an start_tutor.sh.',
            'vollstaendige_bedingungen': 'Siehe Launcherquelltexte und Batch-Labelinventar im Anhang.'
        }
    },
    'seiten': {},
}

DOC['seiten']['start'] = {
    'datei': 'app/frontend/start.html', 'struktur': ['Sprachauswahl', 'Markenlogos', 'Begrüßung und Beschreibung', 'vier Aktionsbuttons', 'Setup-Modal'],
    'elemente': [element('languageCountrySelect', 'Tutorsprache über Land auswählen', 'English-Default; /config liefert Länder. Landesname wird auf Sprachname gemappt.'), element('startButton', 'Schritt 1 öffnen', 'Nur wenn API konfiguriert und Setup ready; sonst Setup-Modal.'), element('infoButton', 'Anleitung öffnen', 'Navigation info.html.'), element('projectButton', 'Projektinfo öffnen', 'Navigation project-info.html.'), element('settingsButton / configureApiKeyButton', 'Lokale Administration', 'Navigation settings.html.'), element('apiKeyModalBackdrop', 'Setup-Hinweis', 'Wird bei fehlendem Schlüssel, Paketen, Ordnern oder fehlgeschlagener Statusabfrage geöffnet; kein allgemeiner Schließen-Handler.')],
    'initialisierung': ['Bei jedem Laden von app.js Sprache auf English und Sprachland auf leer setzen.', 'Einmal pro sessionStorage-Sitzung alte Unterrichts-/Dialogschlüssel entfernen.', 'Sprache und Setup-Status per GET laden; keine KI-Anfrage beim Startseitenladen.'],
    'sprachgrenze': 'Landzuordnung unterstützt mehr Sprachnamen als die acht UI-Sprachen; unbekannter UI-Sprachname führt zu englischer Oberfläche.'
}
DOC['seiten']['unterrichtskontext'] = {
    'datei': 'app/frontend/lesson-info.html', 'schritt': 1,
    'struktur': ['Header mit Logos und Hilfe', 'vierstufige Fortschrittsanzeige', 'Formular und seitliche Warum-wir-fragen-Hilfe', 'Land', 'Fächer und Stufe/Alter', 'Besonderheiten und Upload', 'Back/Continue mit Analyseindikator'],
    'felder': [
        element('country', 'Pflicht-Landesauswahl', 'Option Other aktiviert countryOther. Liste aus /config; Fehlerfallback Slovakia/Germany/Austria/Spain.'),
        element('countryOther / addCountryButton', 'Neues Land eingeben und speichern', 'Feld nur bei Other; Button nur bei nicht leerem Text. Erfolgszweig aktualisiert Liste und wählt neues Land.'),
        element('subjectCheckboxes', 'Mindestens ein Fach auswählen', 'Mehrfachcheckboxen, aus /config; Other mit Freitext.'),
        element('subjectOther / addSubjectButton', 'Eigenes Fach', 'Other muss aktiviert und Text nicht leer sein; Speichern baut Checkboxliste neu und wählt neuen Eintrag.'),
        element('gradeFrom', 'Pflicht-Schulstufe', 'Nicht leer, numerischer Wert muss truthy sein; Ziffernbereinigung.'),
        element('gradeTo', 'Optionale obere Schulstufe', 'Wenn angegeben numerisch und >= gradeFrom.'),
        element('ageFrom / ageTo', 'Optionales Alter', 'Beide leer oder beide befüllt; numerisch und Von <= Bis. Einzelnes Alter nur durch gleiche Werte in beiden Feldern.'),
        element('specifics', 'Besonderheiten/Bedürfnisse/Projektfokus', 'Optionaler Freitext; wird im Kontext und Einstieg des Refinements berücksichtigt.'),
        element('lessonPlanUpload / fileDropzone', 'Originalplan wählen', 'PDF/DOCX/TXT; Klick oder Drop. Ausgewertet wird erster File-Eintrag. Obergrenze 20*1024*1024 Bytes im Client.'),
        element('continueButton', 'Analyse auslösen', 'Erst vollständige validateForm; dann sperren, alte Sitzung löschen, optionale Länder-/Fachspeicherung, Hello-Test, Analyse.'),
        element('fileErrorDetail', 'Diagnose anzeigen', 'Backend-detail oder Rohantwort bei Fehler.'),
        element('analysisHello', 'KI-Test/Ladeanzeige', 'Hello-Antwort, Spinner und Screenreadertext; Fehleranzeige bei Fehlschlag.')
    ],
    'validierung': ['Formular novalidate: maßgeblich ist JavaScript.', 'Fehlermeldungen pro Feld und rote Beschriftung.', 'Zifferngruppen werden zusammengefügt: z.B. 4-6 in einem Feld würde 46 ergeben.', 'Keine maximale Schulstufe bzw. Altersgrenze definiert.', 'Nicht numerische Eingabe löst Browser-alert aus.', '20-MiB-Limit wird nicht im handle_analyze als hartes Backend-Limit wiederholt.'],
    'navigation': {'back': 'start.html', 'hilfe': 'info.html', 'erfolg': 'first-analysis-and-suggestions.html', 'fehler': 'Auf Schritt 1 bleiben und Continue wieder freigeben.'}
}
DOC['seiten']['analyse'] = {
    'datei': 'app/frontend/first-analysis-and-suggestions.html', 'schritt': 2,
    'struktur': ['Header/Hilfe und Fortschritt', 'Analysefehler oder Analyseinhalt', 'Zusammenfassung', 'sechs Analyse-Fokus-Karten', 'detaillierte Kategorien', 'CT-Tabelle', 'Zusatzupload', 'Next-step-Hinweis', 'Analysedownload und Back/Continue', 'Belegstellen- und Datenschutzmodal'],
    'datenquelle': 'localStorage step2Analysis und step2UploadMeta; keine neue Analyse beim Seitenladen.',
    'uebersicht': {'kategorien': ['time_scope', 'goals_competencies', 'adaptability', 'detail_level', 'target_group', 'curriculum_alignment'], 'pro_karte': ['Label', 'Match /10', 'Confidence', 'Status', 'Begründungsnotiz'], 'farblogik': 'Zahl priorisiert: 1–3 rot, 4–6 gelb, 7–10 grün; sonst lexikalische Marker in Status/Notiz. Zahlen gerundet und auf 1..10 begrenzt.'},
    'kategorietabelle': {'max_punkte_pro_kategorie': 8, 'spalten': ['Focus on this? Checkbox', 'Identified point mit Erklärung', 'Why we mentioned this', 'Citation from your text', 'Confidence mit Match', 'Discussion'], 'belegstellen': 'Button öffnet gelieferten Zitatausschnitt und Kontext; keine automatische Prüfung von Seiten-/Zeilennummern.', 'fallback': 'Fehlen categories, werden ältere Analysefelder über Fallback-Kategorien dargestellt.'},
    'punktdiskussion': {'pro_punkt': ['Dialognachrichten', 'Textarea', 'Send', 'Entscheidungs-Select', 'Include in download Checkbox'], 'entscheidungen': ['', 'Keep as is', 'Change', 'Add clarification', 'Not applicable', 'Needs more information'], 'senden': 'Klick oder Ctrl/Meta+Enter; leere Eingabe ignorieren, Send während Request sperren.', 'request': 'POST /analysis-discuss mit Punkt, Kontext, Zusammenfassung, Analysefokus, Gespräch und letzter Nachricht.', 'ergebnis': 'Tutorantwort, Entscheidung, Zusammenfassung und optional Adaptation speichern; Adaptation als eigene Tutorzeile anzeigen.', 'download_auswahl': 'Include in download steuert Bericht; Punktwahl für Refinement ist davon unabhängig.', 'refinement_auswahl': 'Checkbox ODER vorhandene Gesprächsnachrichten; dadurch wird diskutierter Punkt auch unmarkiert übernommen.'},
    'ct': {'reihenfolge': ['Decomposition', 'Pattern recognition / generalisation', 'Abstraction', 'Algorithmic thinking', 'Testing / debugging / evaluation', 'Data / representation'], 'statuses': ['Present', 'Opportunity', 'Not identified'], 'uebersicht': ['Denkpraktik', 'Status', 'Aktivität', 'Discussion / clarification'], 'details': ['Evidence immer', 'Limitation wenn vorhanden', 'Possible refinement wenn vorhanden, sonst Positive note'], 'interaktion': 'Native details/summary pro Zeile; alle sechs Zeilen vorhanden.', 'klaerungsfeld': 'Textarea ausschließlich bei Status Not identified; kein direkter CT-API-Chat.', 'uebergabe': 'Nicht leere Textareas -> category_id computational_thinking, Titel Clarify <practice>, teacher_comment. Keine allgemeine CT-Auswahlcheckbox für Present/Opportunity.'},
    'privacy': {'quelle': 'Markerheuristik in notes_for_teacher, next_step, short_summary und confidence.note.', 'generische_ausnahmen': 'Einige englische Platzhalterformulierungen werden ohne konkrete Identifikator-Marker unterdrückt.', 'modal': 'Öffnung nach 250 ms; blockiert Continue bis Beispiele bestätigt.', 'bestaetigung': 'Continue - examples only setzt privacyExamplesConfirmed und schließt erzwungen.', 'schliessen': 'Escape/Backdrop dürfen ohne Bestätigung nicht schließen.', 'uebergabe': 'Gespeicherter Hinweis wird weiterhin als erster target_group-Refinementpunkt privacy-data-removal ergänzt.'},
    'zusatzupload': {'formate': ['pdf', 'docx', 'txt'], 'mehrfach': True, 'drop': True, 'metadaten': 'Name, Größe, MIME im Browser; File-Objekte nur im Seitenzustand.', 'reload': 'Gespeicherte Namen stellen File-Objekte nicht wieder her; Dateien müssen für tatsächlichen Upload noch ausgewählt sein.', 'verarbeitung': 'Bei Continue an /step2-prepare übermittelt und auf Disk gespeichert; keine automatische Textextraktion oder Promptintegration.'},
    'download': 'POST /export-analysis-docx mit Analyse, Metadaten, Punktdialogen und CT-Klärungen; Button während Generierung sperren.',
    'continue': 'Privacy prüfen -> Auswahl sammeln -> Multipart an /step2-prepare -> step2Preparation speichern -> Refinement; währenddessen Saving und Link deaktiviert.',
    'modalbedienung': 'Belegmodal schließt per Button, Backdrop oder Escape; Privacy mit zusätzlicher Freigabebedingung.'
}
DOC['seiten']['refinement'] = {
    'datei': 'app/frontend/refining-and-improving.html', 'schritt': 3,
    'struktur': ['Header/Hilfe und Fortschritt', 'Einleitung/Kontext', 'Refinement overview mit Fortschrittsbalken', 'anklickbare Themenchips', 'Dialog links', 'Entwurfsvorschau rechts', 'Back/Continue', 'Änderungsmodal'],
    'initialisierung': ['Kontext, Analyse, Auswahl und Vorbereitung lokal laden.', 'Sitzungs-ID mit gespeicherter vergleichen; bei Wechsel lokalen Draft/Chat/Fortschritt verwerfen.', 'Serverzustand laden; bei Verfügbarkeit zuerst übernehmen.', 'Ohne Entwurf feste Basisvorlage erstellen.', 'Themenknoten bilden, UI rendern, lokale Begrüßung/erste Frage oder Gespräch fortsetzen.'],
    'basisentwurf': {'quelle': 'buildBaseDraft, keine vollständige strukturierte Übernahme des Originalplans.', 'titel': 'Analyse-Kurzzusammenfassung oder Lesson plan draft.', 'ziele': ['Clarify the main learning goal for the lesson.', 'Make the connection between task and outcome easier to follow.'], 'skills': ['Critical thinking', 'Problem solving', 'Communication'], 'schritte': [{'titel': 'Introduction', 'minuten': 15}, {'titel': 'Input & Example', 'minuten': 15}, {'titel': 'Inquiry Phase', 'minuten': 20}, {'titel': 'Group Sharing', 'minuten': 15}, {'titel': 'Consolidation', 'minuten': 15}, {'titel': 'Reflection', 'minuten': 10}], 'summe_minuten': 90, 'weitere_felder': 'Generische Materialien, Beobachtung/Exit-Ticket/Präsentationskriterien und generische Reflexion.'},
    'themenbildung': ['Bekannte ausgewählte Kategorien in Auswahlreihenfolge übernehmen.', 'Nur erster ausgewählter Punkt je Kategorie wird eigener Knoten.', 'Einige generische Privacy-Warnungen ausfiltern.', 'Wenn kein bekannter Auswahlknoten vorhanden und analysis.categories existiert: sechs Standardkategorien mit erstem Analysepunkt.', 'Nur wenn weiterhin kein Knoten existiert: sonstige Auswahltitel als generische Knoten.', 'Wenn weiterhin leer: Timing-Fallback.'],
    'standardthemenfolge': ['time_scope', 'goals_competencies', 'adaptability', 'curriculum_alignment', 'detail_level', 'target_group'],
    'ct_besonderheit': 'computational_thinking ist nicht in categoryMap. Bei üblicher vorhandener analysis.categories greift der Sechs-Kategorien-Fallback vor dem generischen CT-Fallback. CT-Kommentare sind im selections-Payload, werden aber nicht zuverlässig eigener aktiver Themenknoten.',
    'uebersicht': {'anzeigen': ['Anzahl/Prozent anhand currentNodeIndex', 'aktuelles Thema', 'nächstes Thema', 'letzte Änderung', 'Status'], 'grenze': 'Fortschritt bildet Index ab, kein unabhängiger Erledigtstatus pro Thema; Sprünge beeinflussen Anzeige.'},
    'themenchips': 'Klick setzt Index/Fokus, zeigt Quick Replies und scrollt zu bestehendem Gespräch oder ergänzt Einstieg; gesperrt während KI-Request.',
    'dialog': {'eingabe': 'Freitext per Formular; leer oder busy ignorieren.', 'quick_replies': 'Klick sendet direkt, intern englisches Label; sichtbares Label übersetzbar.', 'lokaler_keep_pfad': 'Bestimmte englische Keep/Skip-Antworten protokollieren, Entwurf behalten und ohne API weitergehen.', 'normaler_pfad': 'Lehrkraftnachricht lokal speichern -> Scope-Prompt ergänzen -> busy -> /step3-refine -> Antwort prüfen -> Update anwenden -> Tutorantwort -> bleiben/weiter.', 'weiterregel': 'advance fehlt oder ist nicht false: weiter; nicht leere quick_replies erzwingen bleiben.', 'ende': 'Kein aktives Thema nach letzter Frage; Freitext bleibt möglich und führt weiter zu API.', 'clear': 'Browserconfirm; Gespräch und Index zurücksetzen, Entwurf und Änderungen behalten.'},
    'vorschau': {'tabs': ['goals', 'skills', 'steps', 'materials', 'assessment', 'reflection'], 'bearbeitung': 'Lesende Vorschau; keine direkte Richtext-/Tabellenbearbeitung.', 'darstellung': 'Metadaten immer, Abschnittskarten mit Ready/Updated, Schrittstatus, Dauer und Notizen.', 'aenderungen': 'Aus Modelländerungen und zusätzlich Feldvergleich abgeleitet; Tabs/Abschnitte/Schritte markieren.', 'txt_export': 'exportDraft erzeugt lokal lesson-plan-draft.txt; keine Server-/KI-Anfrage.'},
    'antwortkontrollen': {
        'wortlaut': 'Bei erkannter Wording-/Abschnittsanfrage: reine Überschrift/unter fünf Wörter und kein relevantes Draft-Update -> nicht weiter, Hinweis und erneute Antwortoptionen.',
        'zeit_scope': 'Titel, Zusammenfassung, Meta, Ziele, Skills, Materialien, Assessment, Reflexion und Schritttexte erhalten; Dauer, Status, Note übernehmen.',
        'gesamtdauer': 'Kleinere Gesamtdauer ablehnen/zurücksetzen.', 'knappe_zeit': 'Einzelschrittkürzungen anhand englischer Kontextmarker abweisen.',
        'behauptete_mehrzeit': 'Wenn Tutor Minutenaddition behauptet, Draft aber nicht länger ist: erkannte Minuten auf dritten bzw. letzten Schritt addieren.',
        'expliziter_split': 'A+B mindestens Originalsumme: A auf erste zwei Schritte 43/57, B auf übrige verteilen; Notizen Lesson 1/2; Erzwingung advance=true.',
        'merge': 'Nicht leere Listen ersetzen Listen; leere goals/skills/materials/assessment/steps/changes werden nicht als Löschauftrag angewandt. Meta wird zusammengeführt.'
    },
    'busy': 'Textarea, Send und Quick Replies deaktiviert, Thinking-Text, Spinnerklasse und aria-busy.',
    'navigation': 'Continue speichert lokal und führt zu download-result.html, ohne Pflicht alle Themen abzuarbeiten.'
}
DOC['seiten']['download'] = {
    'datei': 'app/frontend/download-result.html', 'schritt': 4,
    'struktur': ['Header/Hilfe/Fortschritt', 'Vollständige strukturierte Vorschau', 'Print/Copy/DOCX/PDF/Finish', 'Änderungsseitenleiste', 'Stärkenseitenleiste', 'gemeinsames Änderungs-/Stärkenmodal'],
    'quelle': 'Draft, Gespräch und Vorbereitung aus localStorage.',
    'vorschau': ['Goals', 'Skills', 'Steps mit Dauer/Status/Notiz', 'Materials', 'Assessment', 'Reflection'],
    'seitenleisten': {'aenderungen': 'Erste sechs Einträge plus Anzahl; vollständiger Verlauf im Modal.', 'staerken': 'Fünf fest codierte Einträge aus getInitialStrengths, nicht aus Analyse.'},
    'aktionen': [element('printPreviewButton', 'Browserdruck', 'window.print; Layout abhängig von Browser und CSS.'), element('copyClipboardButton', 'Teiltext kopieren', 'Nur Titel, Zusammenfassung, Ziele und Schritttitel/Dauern; keine Materialien/Assessment/Reflexion/Schrittbeschreibungen.'), element('downloadDocxButton / downloadPdfButton', 'Export anfordern', 'JSON an jeweilige API; aktueller Button sperren; Blob mit lesson-plan-final.docx/pdf herunterladen.'), element('viewAllChangesButton / viewAllStrengthsButton', 'Details ansehen', 'Gemeinsames Modal mit passendem Titel/Inhalt; Close, Escape, Backdrop.'), element('finishButton', 'Abschluss', 'Vier Step-3-localStorage-Schlüssel löschen, nach start.html; Serverdaten bleiben.')],
    'fehler': 'Fehlender Draft: Rückkehrhinweis; Export kann bei vorhandener Sitzungs-ID Serverzustand verwenden. Server-HTML-Fehler wird bereinigt als Status angezeigt.'
}
DOC['seiten']['settings'] = {
    'datei': 'app/frontend/settings.html', 'struktur': ['Logos', 'Local administration', 'Mistral-/Curricula-/Logstatus', 'Systemcheck', 'Promptpfade', 'KI-Verbindungsformular', 'Back to start'],
    'systemcheck': ['API-Key vorhanden', 'docx/pypdf/reportlab importierbar', 'Frontend/Output/Exports-Ordner vorhanden', 'Pythonversion'],
    'felder': [element('mistralApiUrl', 'Endpoint', 'URL-input; leere Eingabe ändert bisherigen Wert nicht.'), element('mistralModel', 'Modell', 'Text-input; leere Eingabe ändert bisherigen Wert nicht.'), element('mistralApiKey', 'Lokaler Schlüssel', 'Password-input, autocomplete off, nie vorbefüllt; leer erhält alten Schlüssel.')],
    'speichern': 'POST /settings -> speichern -> Feld für Schlüssel leeren -> Status aktualisieren; kein Verbindungstest beim Speichern.',
    'promptanzeige': 'Statusliste erfasst drei Prompts; analysis_discussion_system_prompt.txt existiert, wird hier aber nicht gelistet.',
    'kein_editor': 'Promptdateien werden nur als lokale Pfade gezeigt. Kein UI-Editor für Promptinhalte.',
    'zugriff': 'Keine Login-/Rollenprüfung im Handler; Admin ist UI-Bezeichnung.'
}
DOC['seiten']['info'] = {'datei': 'app/frontend/info.html', 'funktion': 'Statische Anleitung für Download/Start/API-Key und vier Arbeitsschritte mit Screenshots; Links/Struktur exakt im DOM-Inventar.', 'ki_aufruf': False}
DOC['seiten']['projektinfo'] = {'datei': 'app/frontend/project-info.html', 'funktion': 'Statische Projektbeschreibung und Logos/Verweise; konkrete Inhalte im DOM-Inventar und Quelltext.', 'ki_aufruf': False}

DOC['ablauf_und_zustandsautomat'] = [
    record('Startseite DOMContentLoaded', 'immer', 'English setzen, Session-Reset ggf. durchführen, /config und /settings-status laden', 'Startbutton freigeben nur logisch über Statusprüfung'),
    record('Schritt 1 laden', 'immer', 'Config laden, Formhandler registrieren', 'Warten auf Lehrkrafteingabe'),
    record('Continue Schritt 1', 'validateForm false', 'Feldfehler anzeigen', 'Kein Upload und kein KI-Aufruf'),
    record('Continue Schritt 1', 'validateForm true', 'Busy; alte Sitzung löschen; neue Länder/Fächer optional speichern', 'Speicherfehler bei neuen Auswahlwerten blockieren Analyse nicht'),
    record('Analyse beginnen', 'Hello-Test erfolgreich', 'POST /analyze mit Dokument und Kontext', 'Backend extrahiert max. erste 30000 Zeichen für KI und speichert vollständige Datei'),
    record('Analyse beginnen', 'Hello-Test scheitert', 'Fehler zeigen', 'Keine /analyze-Anfrage'),
    record('Analyseantwort', 'HTTP-Erfolg und verarbeitbare Antwort', 'step2Analysis und step2UploadMeta lokal speichern', 'Zu Schritt 2 navigieren'),
    record('Schritt 2 laden', 'Analyse fehlt/enthält error', 'Fehleransicht', 'Keine neue KI-Anfrage'),
    record('Schritt 2 laden', 'Analyse vorhanden', 'Zusammenfassung, Fokus, Kategorien, CT rendern; Privacy prüfen', 'Punktwahl/Dialogs/Upload möglich'),
    record('Analysepunkt senden', 'nicht leere Nachricht', 'Nachricht lokal speichern, /analysis-discuss', 'Antwort/Entscheidung/Adaptation speichern; keine Planänderung'),
    record('Continue Schritt 2', 'Privacy aktiv und nicht als Beispiele bestätigt', 'Modal zeigen', 'Schrittwechsel blockiert'),
    record('Continue Schritt 2', 'Privacy freigegeben', 'Auswahl und CT-Klärungen sammeln, Zusatzdateien/Metadaten an /step2-prepare', 'Neue sessionId und Vorbereitung lokal, Schritt 3'),
    record('Schritt 3 initialisieren', 'Server-Snapshot vorhanden', 'Snapshot übernimmt Draft/Chat/Fortschritt', 'Bootstrap'),
    record('Schritt 3 initialisieren', 'kein Draft vorhanden', 'Festen Basisentwurf anlegen', 'Lokale Begrüßung und Themenstart, kein initialer KI-Aufruf'),
    record('Antwort Schritt 3', 'erkannte Keep/Skip-Antwort mit aktivem Thema', 'Lokal protokollieren und Thema weiter', 'Kein /step3-refine, kein neuer Serversnapshot'),
    record('Antwort Schritt 3', 'normal, nicht leer und nicht busy', 'Scoped UserMessage, vollständiger Payload -> /step3-refine', 'Server speichert Rohresultat bevor Frontend es begrenzt'),
    record('Refinementantwort', 'Wording unvollständig oder Zeitprüfung verletzt', 'Hinweis und Optionen; keine akzeptierte entsprechende Entwurfsänderung', 'Im Thema bleiben'),
    record('Refinementantwort', 'Update akzeptiert', 'Merge, Diff-Marker, Tutorantwort, lokal persistieren', 'advance false/Quick Replies: bleiben; sonst weiter'),
    record('Themensprung', 'kein Request läuft', 'Index/Fokus setzen und lokal persistieren', 'Keine automatische Serverzustandsaktualisierung'),
    record('Clear conversation', 'Browserconfirm ja', 'Chat/Fortschritt lokal leeren', 'Draft bleibt; vorhandener Serversnapshot wird dadurch nicht gelöscht'),
    record('Continue Schritt 3', 'beliebiger Bearbeitungsstand', 'Browserzustand speichern', 'Downloadseite'),
    record('Downloadseite laden', 'lokaler Draft vorhanden', 'Vorschau und feste Stärken rendern', 'Kein KI-Aufruf'),
    record('DOCX oder PDF', 'Draft oder sessionId vorhanden', 'Serverbundle mit beiden Formaten erzeugen', 'Jeweils angefordertes Format ausliefern'),
    record('Finish', 'immer', 'Step-3-Browserzustand löschen und Startseite öffnen', 'Serverdateien/Snapshots/Logs bleiben erhalten')
]

DOC['prompting'] = {
    'mechanismen_und_beabsichtigter_nutzen': [
        {'mechanismus': 'Getrennte Systemprompts', 'nutzen': 'Analyse, Punktdiskussion, Refinement und Test haben eigene Aufgaben und Ausgabeformen.'},
        {'mechanismus': 'UI-Kontext vor Rohdokument', 'nutzen': 'Verhindern, dass Dokumentlabels den ausgewählten Unterrichtskontext verdrängen.'},
        {'mechanismus': 'Sprachregel mehrfach im Analysekontext', 'nutzen': 'Analyse in gewählter Tutorsprache, enums/JSON-Keys stabil.'},
        {'mechanismus': 'Evidenzpflicht', 'nutzen': 'Rückmeldung an konkrete Aktivitäten und Textstellen binden.'},
        {'mechanismus': 'Kontrollierte Kategorien/Status und JSON-Beispiel', 'nutzen': 'Maschinenlesbare, vorhersagbare Felder für UI.'},
        {'mechanismus': 'Maximal acht Analysepunkte pro Kategorie', 'nutzen': 'Priorisierung und begrenzte Tabellenlänge; UI begrenzt zusätzlich.'},
        {'mechanismus': 'CT-Handlungen statt Schlagwörter', 'nutzen': 'Technologieeinsatz oder Lehrerhandlung nicht automatisch als CT zählen.'},
        {'mechanismus': 'Memory-Summary vor Rohpayload', 'nutzen': 'Entscheidungen, Änderungen und Dialogkontinuität hervorheben.'},
        {'mechanismus': 'Fokus als Bearbeitungsgrenze', 'nutzen': 'Ungefragte Änderungen anderer Planabschnitte begrenzen.'},
        {'mechanismus': 'Wording-Aufträge und UI-Nachprüfung', 'nutzen': 'Verhindern, dass Überschriften als fertige Formulierungen ausgegeben werden.'},
        {'mechanismus': 'Zeitregeln in System- und Userprompt sowie im UI', 'nutzen': 'Zeitprobleme nicht durch unerwünschtes Kürzen lösen.'},
        {'mechanismus': 'Temperatur 0.2 und response_format json_object', 'nutzen': 'Geringere Ausgabevariation und besser parsebares JSON.'},
        {'mechanismus': 'Lokale JSON-Reparatur und einmaliger Modellreparatur-Aufruf', 'nutzen': 'Einige formal fehlerhafte Antworten weiter nutzbar machen.'},
        {'mechanismus': 'HTTP-400-Fallback ohne response_format', 'nutzen': 'Analyse/Refinement mit kompatiblen Endpoints ohne diesen Parameter versuchen.'}
    ],
    'request_form': {'modell': 'config.MISTRAL_MODEL', 'messages': ['system: geladene Promptdatei', 'user: Kontext/Summary + serialisierte Daten'], 'temperature': 0.2, 'response_format': {'type': 'json_object'}, 'max_tokens': 'Nicht explizit gesetzt.', 'conversation': 'Dialog als Daten im Userprompt; keine separate historische Rolle je Nachricht im API-messages-Array.'},
    'analyse': {
        'datei': 'app/server/prompts/analysis_system_prompt.txt', 'rolle': 'Curriculum analysis assistant for teachers',
        'input': ['Teacher-entered UI target context als lesbare Übersicht', 'Full uploaded lesson payload als eingerücktes JSON', 'Dokumenttext begrenzt auf 30000 Zeichen'],
        'prioritaeten': ['UI-Kontext bestimmt Ziel.', 'Dokumentbehauptungen separat extrahieren.', 'Tätigkeiten bestimmen reale Schwierigkeit, Zeit und Zielgruppenpassung.', 'Ausgewählte Fächer als Hauptlinse; andere Fächer als unterstützender Kontext.'],
        'zeit': 'Aufbau, Übergänge, Messungen, Fehlversuche, Reflexion, Poster, Präsentation und Gruppenmanagement berücksichtigen.',
        'zielgruppe': 'In-range-Schulstufe nicht allein wegen breiterem Dokumentbereich als unpassend einstufen; Fachmismatch separat.',
        'curriculum': 'Fehlende Referenz von belegtem Widerspruch trennen; keine starke explizite Passung ohne Beleg, keine erfundenen Codes/Zitate.',
        'arts_mathematik': 'Konkrete Kunsthandlungen zählen; mathematische Handlungen in fächerübergreifender Stunde separat prüfen.',
        'scores': {'1_3': 'poor fit/critical mismatch', '4_6': 'partial fit/needs adaptation', '7_10': 'good fit'},
        'privacy': 'Nur konkret identifizierbare Daten melden; Platzhalter nicht; Datentyp nennen.',
        'ct': {'present': 'Aktivität + Evidenz; positive_note nötig, sofern kein hilfreiches Refinement.', 'opportunity': 'Verwandte vorhandene Aktivität; Aktivität/Evidenz/Einschränkung/konkretes Refinement erforderlich.', 'not_identified': 'Nur wenn keine verwandte Lernaktivität im gesamten Plan existiert; activity und refinement leer; Evidenz und limitation erforderlich.', 'besonderheiten': ['Befolgen einer festen Anleitung allein ist kein algorithmisches Denken.', 'Rezepte, Materialien, Mengen, Texturen und Ergebnisse vergleichen kann Muster/Testen/Daten-Potenzial sein.', 'Keine normativen Formulierungen wie poor/bad/critical/insufficient für CT-Einschränkungen.']},
        'output': 'Nur Roh-JSON; sechs Fokusobjekte, genau sechs CT-Einträge, bekannte Kategorien, Match-Werte, Belege und konkrete Maßnahmen/Stärken.',
        'kontrolle': 'Backend normalisiert CT-Form/Status, prüft aber nicht die vollständige semantische Erfüllung aller Promptregeln.'
    },
    'punktdiskussion': {
        'datei': 'app/server/prompts/analysis_discussion_system_prompt.txt', 'input': ['Genau ein Punkt mit Evidenz', 'Unterrichtskontext', 'Analysesummary/-fokus', 'Punktgespräch', 'Letzte Lehrkraftnachricht'],
        'regeln': ['Genau einen Punkt diskutieren.', 'Plan nicht umschreiben und keine Evidenz erfinden.', 'Korrektur der Lehrkraft anerkennen und Summary aktualisieren.', 'Aktuelle Nachrichtensprache verwenden.', 'Kurz, konkret, respektvoll.', 'Bei Fach-/Curriculum-/Zielgruppenmismatch eine konkrete kontextbezogene Adaptation nennen.', 'Ohne Curriculumreferenz fehlenden Beleg offen nennen.'],
        'output_felder': ['assistant_message', 'decision', 'summary', 'adaptation_proposal', 'include_in_download'],
        'include_in_download': 'true bei Entscheidung, Korrektur, wichtigem Kontext oder konkreter Verbesserung; false nur bei prozeduralem/nicht hilfreichem Austausch.',
        'fallback_grenze': 'Anders als Analyse/Refinement kein expliziter HTTP-400-response_format-Retry im Discussion-Aufruf.'
    },
    'refinement': {
        'datei': 'app/server/prompts/refinement_system_prompt.txt',
        'memory': {'vorangestellt': True, 'letzte_aenderungen': 8, 'letzte_nachrichten_in_summary': 10, 'felder': ['sessionId', 'Land/Fächer', 'aktiver Fokus', 'letzte Antwort', 'bereits umgesetzte Änderungen', 'recent conversation', 'Kontinuitätsanweisung'], 'grenze': 'Vollständiger Gesprächs-Payload folgt zusätzlich; Summary reduziert hier nicht automatisch die gesamte Tokenmenge.'},
        'input': ['Aktueller Entwurf', 'Fokuspunkt', 'Analysefelder und Kontext', 'Gesamtes Gespräch', 'Letzte Eingabe', 'Fortschritt/Sitzung/Originaldateimetadaten'],
        'regeln': ['Bestehenden Draft verwenden.', 'Aktiven Fokus als Grenze beachten.', 'Freies Anliegen ohne Fokus direkt beantworten.', 'Entscheidungen, Präferenzen, Einschränkungen und Ablehnungen bis Änderung als verbindlich behandeln.', 'Vor Frage/Optionen bereits getroffene Entscheidungen und ausgeschlossene Alternativen prüfen.', 'Keine geklärten Präferenzfragen neu eröffnen.', 'Klaren Änderungsauftrag sofort anwenden; nur entscheidende fehlende Angabe nachfragen.', 'Wenn Rückfrage nötig: eine kurze Frage und zwei bis vier passende Optionen, sonst leeres Array.', 'Wording-Anfrage mit tatsächlichem Wortlaut beantworten.', 'Explizite Abschnittsänderung in updated_draft eintragen und changes dokumentieren.', 'Bei personenbezogenem Fokus Anonymisierung/Entfernung zuerst behandeln.', 'Aktuelle Nachrichtensprache verwenden.', 'Jede Änderung mit belegtem Ort/Abschnitt, keine erfundene Seitenzahl.'],
        'zeitregeln': ['time_scope nur Dauer/Notiz/Status/Sessiongruppierung.', 'Gesamtdauer niemals verringern.', 'Bei tight Einzelschritte nicht kürzen.', 'Explizite Aufteilung unmittelbar anwenden.', 'Summe prüfen; Sessionaufteilung fachlich/curricular kohärent halten.', 'Keine behauptete Curriculumkonformität ohne Evidenz.'],
        'output_felder': ['assistant_message', 'advance', 'focus_used', 'quick_replies', 'updated_draft', 'changes_made'],
        'prompt_vs_code': 'Prompt lässt explizit angefragte Inhaltsänderungen auch im Timingfokus zu; constrainUpdatedDraft erhält solche Inhalte trotzdem im Timingfokus. Abweichung dokumentiert.'
    },
    'hello': {'datei': 'app/server/prompts/mistral_test_system_prompt.txt', 'system': 'Reply with exactly: hello', 'user': 'Say hello.', 'temperature': 0, 'response_format': 'nicht gesetzt', 'ziel': 'https://api.mistral.ai/v1/chat/completions fest codiert', 'antwort': 'Rohtext als hello-Feld; nicht derselbe JSON-Vertrag wie Analyse.'},
    'json_reparatur': {'lokal': ['Codefences/umgebenden Text entfernen', 'JSON parsen', 'Häufige Syntax-/Quoteprobleme reparieren'], 'modell': 'Nur bei Parseexception weiterer Request: ungültiges JSON reparieren, Keys/Werte möglichst erhalten, nur Roh-JSON.', 'objektpruefung': 'Nicht-Objekt und fehlender Block können Fehlerobjekt ergeben.', 'wiederholung': 'Kein allgemeiner Backoff oder beliebiger Netzwerkretry implementiert.'},
    'vollstaendige_prompts': {p.name: read(p.relative_to(ROOT).as_posix()) for p in sorted((ROOT / 'app/server/prompts').glob('*.txt'))}
}

DOC['datenvertraege'] = {
    'analysis': {'screen': 'first_analysis_and_suggestions', 'lesson_plan_summary': ['short_summary', 'detected_subjects[]', 'detected_age_range.from/to', 'detected_grade_range.from/to', 'match_score', 'confidence.level/note', 'notes_for_teacher'], 'analysis_focus': 'Sechs bekannte Kategorien; jeweils status, match_score, confidence, note.', 'computational_thinking': 'Sechs Einträge: practice/status/activity/evidence/limitation/refinement/positive_note.', 'categories': 'id/title/description/items[]', 'item': ['id', 'title', 'short_explanation', 'why_it_matters', 'evidence', 'citation', 'suggested_next_action', 'positive_note', 'match_score', 'confidence', 'teacher_comment_placeholder'], 'citation': ['label', 'page', 'section', 'line_start', 'line_end', 'cited_text', 'context_before[]', 'context_after[]'], 'sourceDocument': 'Nach KI-Verarbeitung vom Backend ergänzt: filename/storedFilename/path.'},
    'selection': ['category_id', 'item_id', 'title', 'teacher_comment'],
    'point_discussion': ['messages[] mit role/text', 'decision', 'summary', 'adaptationProposal', 'includeInDownload'],
    'draft': {'skalare': ['title', 'section', 'summary', 'reflection'], 'meta': ['country', 'subjects[]', 'gradeRange', 'ageRange', 'focus'], 'listen': ['goals', 'skills', 'steps', 'materials', 'assessment', 'changes'], 'step': ['title', 'duration', 'description', 'status', 'note'], 'change': ['kind', 'section optional', 'title', 'reason', 'location', 'beforeValue', 'afterValue', 'source', 'time']},
    'conversation_message': ['role', 'text', 'time', 'extraClass', 'topicId', 'topicLabel'],
    'progress': ['section', 'currentNodeIndex', 'awaitingFreeText'],
    'server_snapshot': ['sessionId', 'draft', 'conversation', 'progress', 'currentNodeId', 'sourceDocument', 'payload', 'result'],
    'refinement_payload': ['sessionId', 'country', 'subjects', 'meta', 'selections', 'filename', 'sourceDocument', 'analysisSummary', 'analysisFocus', 'analysisCategories', 'currentNode', 'progress', 'draft', 'conversation', 'userMessage'],
    'nicht_im_refinement_payload': ['analysis.computational_thinking als vollständiger Block', 'vollständiger extrahierter documentText', 'Text der Zusatzuploads', 'automatisch recherchierte Lehrplantexte']
}

ROUTES = [
    ('GET', '/', 'Startseite ausliefern', 'Kein Payload', 'HTML', '200/404'),
    ('GET', '/ping', 'Erreichbarkeit', 'Kein Payload', '{status: ok}', '200'),
    ('GET', '/config', 'Länder/Fächer', 'Kein Payload', 'config.json', '200/404'),
    ('GET', '/settings-status', 'Systemstatus', 'Kein Payload', 'mistral/email/paths/prompts/runtime', '200'),
    ('GET', '/step3-state', 'Sitzung wiederherstellen', 'sessionId Query', 'Snapshot JSON', '200/400/404'),
    ('GET', '/frontend/*', 'Statische Frontend-Dateien', 'Pfad', 'Datei', '200/403/404'),
    ('GET', '/data/curricula/*', 'Lokale Lehrplandatei', 'Pfad', 'Datei', '200/403/404'),
    ('GET', '/*', 'Sonstiger Frontend-Pfad', 'Pfad relativ frontend', 'Datei', '200/403/404'),
    ('POST', '/upload', 'Optionaler einfacher Upload', 'Multipart file oder lessonPlan + specifics', 'saved / specificsSaved', '201/400/500'),
    ('POST', '/analyze', 'Erste Analyse', 'Multipart Original und Kontext', 'Analyse + sourceDocument oder error', '200/400/422/500/502'),
    ('POST', '/step2-prepare', 'Dateien/Metadaten/Sitzung vorbereiten', 'Multipart Kontext, selections, sourceDocument, additionalFiles', 'prepared/sessionId/Ordner/savedFiles', '200/400/500'),
    ('POST', '/analysis-discuss', 'Einzelpunkt diskutieren', 'JSON point/lesson_context/analysis_summary/analysis_focus/conversation/user_message', 'assistant_message/decision/summary/adaptation_proposal/include_in_download', '200/400/502'),
    ('POST', '/step3-refine', 'Refinement durchführen', 'Refinement JSON', 'assistant_message/advance/focus_used/quick_replies/updated_draft/changes_made', '200/400/502'),
    ('POST', '/export-analysis-docx', 'Analysebericht exportieren', 'JSON analysis/meta/sessionId/discussions/clarifications', 'DOCX-Bytes', '200/400/500'),
    ('POST', '/export-docx', 'Finales DOCX', 'JSON sessionId/filename/draft/conversation/sourceDocument', 'DOCX-Bytes', '200/400/500'),
    ('POST', '/export-pdf', 'Finales PDF', 'JSON wie DOCX', 'PDF-Bytes', '200/400/500'),
    ('POST', '/send-email', 'Optionaler SMTP-Export', 'JSON Änderungspaket/Empfänger/Sitzung', 'Sendeergebnis oder error', '200/400/502'),
    ('POST', '/mistral-test', 'Hello-Test', 'Kein Pflichtpayload', 'hello oder error', '200/502'),
    ('POST', '/client-log', 'Clientdiagnose speichern', 'JSON message', '{saved: true}', '200/400'),
    ('POST', '/config', 'Land/Fach ergänzen', 'JSON newCountry und/oder newSubject', 'saved', '200/400/500'),
    ('POST', '/settings', 'KI-Einstellungen ändern', 'JSON mistralApiUrl/mistralModel/mistralApiKey', 'saved/updated/status oder error', '200/400/500'),
]
DOC['api'] = [{'methode': a, 'pfad': b, 'funktion': c, 'input': d, 'output': e, 'statuscodes': f, 'referenz': 'app/server/app.py'} for a, b, c, d, e, f in ROUTES]

DOC['persistenz'] = {
    'localStorage': {
        'preferredLanguage': 'Gewählte KI-/UI-Sprache; Startseite setzt English.', 'preferredLanguageCountry': 'Sprachland; Startseite leert.',
        'step2Analysis': 'Erste Analyse inklusive Originaldateimetadaten.', 'step2UploadMeta': 'Kontext und Originaldatei.', 'step2Selections': 'Gewählte/disktutierte Punkte und CT-/Privacy-Ergänzungen.', 'step2Preparation': 'sessionId, Land-/Fachordner und gespeicherte Zusatzdateien.', 'step2PointDiscussions': 'Punktgespräche/Entscheidungen, keyed nach Kategorie und Punkt.', 'step2AdditionalUploadMeta': 'Nur Metadaten, keine File-Objekte.', 'step2PrivacyWarning': 'Erkannter Hinweis.', 'step3Draft': 'Akzeptierter Frontend-Entwurf.', 'step3Conversation': 'Sichtbares Gespräch.', 'step3Progress': 'Tab, Themenindex, awaitingFreeText.', 'step3Session': 'Zugehörige sessionId.'
    },
    'sessionStorage': {'tutorSessionInitialized': 'Verhindert mehrmaliges Unterrichtsdaten-Reset innerhalb derselben Browser-Tab-Sitzung.'},
    'dateisystem': {'app/data/config.json': 'Länder/Fächer', 'app/server/.env': 'Nicht geheime KI-Settings und optionale SMTP-Konfiguration; tatsächliche Inhalte nicht dokumentiert.', 'app/server/mistral_api_key.txt': 'Lokaler Schlüssel; Wert nicht dokumentiert.', 'app/data/lessonplans/uploads': 'Vollständiges Original, UUID-Suffix/Slug.', 'app/data/curricula/<country>/<subject>': 'Angelegte Lehrplanablage.', 'app/data/amendments/<country>/step2-<session>': 'Zusatzdateien und step2-metadata.json.', 'app/data/outputs/step3-sessions/<session>.json': 'Server-Snapshot nach KI-Aufruf.', 'app/data/outputs/step3-sessions/<session>-conversation.txt': 'Memory und Gesamtgespräch.', 'app/data/outputs/exports/<session>': 'Analyse-/Final-DOCX/PDF.', 'app/data/outputs/analysis-log.txt': 'Server-/Clientdiagnose', 'app/data/outputs/mistral-prompt-log.txt': 'Vollständige Prompts/Payloads nach API-Schlüsselredaktion.', 'app/data/outputs/server.log': 'Launcher-Serverausgabe.'},
    'resetregeln': ['Neuer Upload entfernt alle bekannten Unterrichts-Browserschlüssel.', 'Neue Sitzung in Refinement verwirft lokalen Step-3-Stand.', 'Clear conversation löscht lokalen Chat/Fortschritt, nicht Draft/Serverdateien.', 'Finish löscht nur vier Step-3-localStorage-Schlüssel.', 'Startseite löscht alle Unterrichts-Browserschlüssel nur bei neuem sessionStorage-Marker.', 'Kein automatisches Löschen alter Uploads, Logs, Snapshots oder Exporte beim Finish.'],
    'zustandsprioritaet': 'Refinement-Init übernimmt verfügbaren Serverzustand. Export bevorzugt Server-Draft vor Payload-Draft; lokale Clientkorrekturen oder Keep/Sprung/Clear können gegenüber Serverstand abweichen.'
}
DOC['export'] = {
    'analyse_docx': 'Summary, Fokus, CT, detaillierte Kategorien, ausgewählte Include-in-download-Punktdiskussionen und Klärungen.',
    'refinement_txt': 'Lokal generierter strukturierter Zwischenstand; keine Originalformatierung.',
    'final_docx': {'vorlage': 'Original-DOCX öffnen, aufgezeichnete Vorher/Nachher-Änderungen in passenden Abschnitten ersetzen.', 'ersetzungen': 'Schrittobjekte: title/duration/description/note; Listen: zip alter/neuer Einträge; Skalar: nicht leere unterschiedliche Werte.', 'eindeutigkeit': 'Abschnittszuordnung zuerst; globaler Fallback nur bei insgesamt genau einem Alttexttreffer.', 'format': 'Run-Ersetzung erhält Format eher; Absatztext-Fallback ohne Zeichnungen kann Runformat verlieren.', 'nicht_gefunden': 'Keine sichere Ersetzung -> Originaltext behalten und Log; kein Beweis, dass jede Preview-Änderung im DOCX landet.', 'fallback': 'Bei Vorlagefehler textbasiertes DOCX.'},
    'final_pdf': {'quelle': 'Originaltext plus Inlineänderungen, aktualisierte Metadaten und ersetzte/ergänzte bekannte Abschnitte.', 'layout': 'A4; Ränder links/rechts 16 mm, oben/unten 18 mm; Helvetica; Titel 20 pt, H2 13 pt, Body 10.5 pt; XML-Escaping.', 'originaltreue': 'Keine originalgetreue PDF-Layoutbearbeitung.'},
    'bundle': 'Jeder DOCX- oder PDF-Endpunkt erstellt beide Formate und ersetzt vorhandene Dateien gleichen Exportnamens.',
    'validierung': 'Existenz/nicht leer, PDF-%PDF-, DOCX gültiges ZIP mit [Content_Types].xml.',
    'dateinamen': 'Backend: normalisierter Draft-Titel bzw. Originalname. Frontend-Download: feste lesson-plan-final.docx/pdf; Content-Disposition wird vom Client nicht als Name übernommen.',
    'optional_email': {'ui': 'Nicht aktiv', 'anhang': ['change-steps.txt', 'pros.txt', 'cons.txt'], 'kein_anhang': ['Unterrichtsplanexport', 'Gesprächsprotokoll'], 'smtp': 'Host/Port/Empfänger; optional Login, STARTTLS oder SMTP_SSL; Timeout 30 s.'}
}
DOC['grenzen_und_abweichungen'] = [
    {'punkt': 'Minimale Inhaltserstellung', 'ist': 'Feste generische Basisvorlage und direkte KI-Updates vorhanden.', 'ziel': 'Lehrkraft möchte möglichst wenig automatische Erstellung.'},
    {'punkt': 'CT-Themenübergabe', 'ist': 'Nur Not-identified-Klärung wird gewählt; CT nicht in bekannten Kategorien; Kategorienfallback kann eigenen CT-Knoten verhindern.'},
    {'punkt': 'Originalplan im Refinement', 'ist': 'Erste Analyse hat Originaltext; Refinement-Payload enthält Summary/Kategorien/Metadaten, keinen vollständigen documentText und keine strukturierte Originalextraktion.'},
    {'punkt': 'Zusatzuploads und Curricula', 'ist': 'Dateien werden abgelegt; Inhalte nicht automatisch im Refinement-Prompt gelesen; keine RAG/Webrecherche implementiert.'},
    {'punkt': 'Stärken auf Downloadseite', 'ist': 'Fünf feste positive Texte statt tatsächlicher initialer Analysebefunde.'},
    {'punkt': 'Clipboard', 'ist': 'Teiltext, obwohl Button allgemeinen Kopierzweck nahelegt.'},
    {'punkt': 'Timing-Inhaltsausnahme', 'ist': 'Prompt erlaubt ausdrückliche Inhaltsänderung; UI-Constrain setzt nicht zeitbezogene Felder dennoch zurück.'},
    {'punkt': 'Split und enge Zeit', 'ist': 'Expliziter Split überschreibt Zeiten und umgeht !explicitSplit-Prüfung auf verkürzte Einzelschritte; Summe muss mindestens original sein.'},
    {'punkt': 'Server-/Browserzustand', 'ist': 'Server speichert Modellrohentwurf vor Frontendprüfungen; lokale Keep/Sprünge/Clear erzeugen keinen Serversnapshot. Serverpriorität bei Reload/Export kann anderen Stand liefern.'},
    {'punkt': 'Mehrsprachigkeit', 'ist': 'UI hat acht Sprachen; Landesmapping mehr. Einige Eingabeprüfungen/Privacy-/Zeit-/Wording-Heuristiken sind englisch, manche dynamische Texte bleiben Englisch.'},
    {'punkt': 'Hello-Endpoint', 'ist': 'Fest auf offiziellen Mistral-Endpunkt, während normale Requests konfigurierbare API nutzen.'},
    {'punkt': 'Promptpfadliste', 'ist': 'Discussion-Prompt nicht in Admin-Statusliste enthalten.'},
    {'punkt': 'Default-Config', 'ist': 'app.py hat benachbarte Python-Stringliterale Italy und Germany ohne Komma, dadurch ItalyGermany bei dortigem Neuaufbau; Windowslauncher legt andere korrekte Liste inklusive Arts an.'},
    {'punkt': 'PDF', 'ist': 'Keine OCR; gescanntes PDF ohne lesbaren Text wird mit 422 abgelehnt.'},
    {'punkt': 'Dokumentumfang', 'ist': 'Analyse-Payload enthält nur erste 30000 Textzeichen; Original vollständig gespeichert.'},
    {'punkt': 'Größenvalidierung', 'ist': '20-MiB-Schranke clientseitig; Backend enthält keine entsprechende explizite Uploadgrenze.'},
    {'punkt': 'Login/Isolation', 'ist': 'Keine Authentifizierung/Autorisierung als Produktfunktion; localStorage nicht pro Benutzerkonto; Sitzungspfad aus übergebener ID gebildet.'},
    {'punkt': 'Privacy-Erkennung', 'ist': 'Prompt plus Markerheuristik; keine sichere automatische Anonymisierung; Dokument wurde vor Warnung bereits gespeichert und an KI übermittelt.'},
    {'punkt': 'Logging', 'ist': 'API-Schlüssel redigiert, aber Dokument-/Dialoginhalte im vollständigen Promptlog nicht automatisch anonymisiert.'},
    {'punkt': 'KI-Regelgarantie', 'ist': 'JSON-Modus ist kein JSON-Schema-/Semantikvalidator; viele Qualitätsregeln nur Prompt.'},
    {'punkt': 'Doppelte Definition', 'ist': 'updateAddSubjectButton zweimal identisch in lesson-info.js; spätere Definition maßgeblich.'},
    {'punkt': 'Inaktive Helfer', 'ist': 'applyConversationReply wird nicht im aktiven Dialog aufgerufen; setBusyState nicht durch exportFile aufgerufen. Funktionsinventar unterscheidet Deklaration von Nachweis eines Aufrufs.'}
]
DOC['besprochene_ct_erweiterung'] = {
    'status': 'Vorschlag, nicht implementiert',
    'ziel': 'Analyse erkennt CT-Potenzial; Refinement unterstützt Lehrkraftentscheidungen und generiert Vorschläge auf Wunsch.',
    'funktionen': ['CT-Punkt bewusst als eigenen Refinement-Fokus übernehmen.', 'Aktivität/Evidenz/Einschränkung/CT-Denkhandlung als Kontext mitgeben.', 'An Ideen der Lehrkraft anknüpfen und eine gezielte Reflexionsfrage stellen, wenn noch eine Entscheidung offen ist.', 'Auf Anfrage eine kleine passende Änderung oder konkreten Wortlaut anbieten.', 'Klare Einfüge-/Änderungsanweisung direkt umsetzen, sonst Vorschlag nicht automatisch übernehmen.', 'Änderungen auf betreffende Aktivität beschränken und CT-Bezug erklären.']
}

# Allowlist prevents accidental inclusion of secret/data files.
FILES = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / 'app/server').glob('*.py'))
FILES += sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / 'app/frontend').glob('*.html'))
FILES += sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / 'app/frontend/js').glob('*.js'))
FILES += ['app/frontend/css/style.css', 'app/server/requirements.txt']
FILES += sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / 'app/server/prompts').glob('*.txt'))
FILES += ['start_tutor.bat', 'start_tutor.sh', 'start_tutor.command', 'run_tests.bat', 'run_tests.sh', 'tests/run_tests.py', 'tests/test_services.py']
FILES = sorted(set(FILES))
SOURCE = {p: read(p) for p in FILES}

DOC['dateistruktur'] = {
    'anwendungsdateien': FILES,
    'assets': sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / 'app/frontend/assets').iterdir() if p.is_file()),
    'datengruppen': ['config', 'curricula', 'amendments', 'lessonplans/uploads', 'templates', 'outputs/exports', 'outputs/step3-sessions'],
    'keine_dateninhalte': 'Upload-/Log-/Schlüssel-/Sitzungsinhalte werden nicht in diese Inventur übernommen.'
}

FUNCTIONS = []
UNEXPLAINED = []
for path, source in SOURCE.items():
    if not path.endswith('.py'):
        continue
    tree = ast.parse(source)
    source_lines = source.splitlines()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        parent_class = next((c.name for c in ast.walk(tree) if isinstance(c, ast.ClassDef) and node in c.body), None)
        name = node.name
        purpose = PURPOSE.get(name)
        if name.startswith('test_'):
            purpose = 'Regressionstest: ' + name[5:].replace('_', ' ') + '. Keine Produktfunktion.'
        elif name in ('setUp', 'tearDown'):
            purpose = 'Testkontext aufbauen bzw. nach Test zurücksetzen.'
        elif name == '__init__':
            purpose = 'Initialisiert Testrunner-Helfer.'
        if not purpose:
            UNEXPLAINED.append(path + ':' + name)
            purpose = ast.get_docstring(node) or 'Siehe konkrete Bedingungen, Rückgaben und Quelltextreferenz.'
        calls = sorted({ast.unparse(n.func) for n in ast.walk(node) if isinstance(n, ast.Call)})
        conditions = [{'zeile': n.lineno, 'bedingung': ast.unparse(n.test)} for n in ast.walk(node) if isinstance(n, (ast.If, ast.While, ast.IfExp))]
        returns = [ast.unparse(n.value) if n.value is not None else 'None' for n in ast.walk(node) if isinstance(n, ast.Return)]
        FUNCTIONS.append(dict(datei=path, sprache='Python', name=name, klasse=parent_class, zeile=node.lineno, ende=node.end_lineno, parameter=ast.unparse(node.args), aufgabe=purpose, docstring=ast.get_docstring(node), aufrufe=calls, entscheidungen=conditions, rueckgaben=returns, genaue_implementierung=f'quelltextreferenz[{path}], Zeilen {node.lineno}–{node.end_lineno}'))


def js_function_matches(source):
    # Include all named declarations and the named global assigned translation callback.
    found = list(re.finditer(r'\bfunction\s+([A-Za-z_$][\w$]*)\s*\(([^)]*)\)\s*\{', source))
    found += list(re.finditer(r'window\.(tutorTranslate)\s*=\s*function\s*\(([^)]*)\)\s*\{', source))
    return sorted(found, key=lambda m: m.start())


EVENTS = []
UI = {}
OPERATIONS = {}
for path, source in SOURCE.items():
    if not path.endswith(('.js', '.html')):
        continue
    # HTML source is retained exactly; JS indexes use original source line numbers.
    for m in js_function_matches(source):
        name = m.group(1)
        purpose = PURPOSE.get(name)
        if not purpose:
            UNEXPLAINED.append(path + ':' + name)
        line = source.count('\n', 0, m.start()) + 1
        occurrences = len(re.findall(r'\b' + re.escape(name) + r'\s*\(', source))
        FUNCTIONS.append(dict(datei=path, sprache='JavaScript', name=name, zeile=line, parameter=m.group(2), aufgabe=purpose or 'Siehe Quelltextreferenz.', syntaktische_namensvorkommen_mit_klammer=occurrences, aufrufstatus='Nur Deklaration im selben Modul gefunden; externe/indirekte Nutzung nicht ausgeschlossen.' if occurrences == 1 else 'Weitere syntaktische Vorkommen im Modul; keine dynamische Laufzeitanalyse.', genaue_implementierung=f'quelltextreferenz[{path}], ab Zeile {line}'))
    rows = source.splitlines()
    for i, row in enumerate(rows, 1):
        if '.addEventListener(' in row:
            match = re.search(r'(.+?)\.addEventListener\(\s*["\']([^"\']+)', row)
            EVENTS.append({'datei': path, 'zeile': i, 'zielausdruck': match.group(1).strip() if match else None, 'event': match.group(2) if match else None, 'registrierung': row.strip(), 'handler_start': '\n'.join(rows[i-1:min(i+5, len(rows))]), 'vollstaendiger_handler': f'quelltextreferenz[{path}], ab Zeile {i}'})
    op = {}
    for label, pattern in {
        'dynamische_dom_erzeugung': r'document\.createElement\([^\n]+',
        'dom_selektoren': r'(?:document|window\.document)\.(?:getElementById|querySelectorAll|querySelector)\([^\n]+',
        'requests': r'fetch\([^\n]+',
        'browser_speicher': r'window\.(?:localStorage|sessionStorage)\.[^\n]+',
        'navigation': r'window\.location\.[^\n]+',
        'dialoge': r'(?:window\.)?(?:alert|confirm)\([^\n]+',
        'zustands_und_sichtbarkeitsentscheidungen': r'[^\n]*(?:\.disabled\s*=|\.hidden\s*=|\.style\.display\s*=|\.classList\.|setAttribute\(["\']aria-|if\s*\()[^\n]*'
    }.items():
        op[label] = [{'zeile': source.count('\n', 0, m.start()) + 1, 'ausdruck': m.group(0).strip()} for m in re.finditer(pattern, source)]
    OPERATIONS[path] = op
    if path.endswith('.html'):
        dom = DOM()
        dom.feed(source)
        UI[path] = {'knoten': dom.nodes, 'bedeutung': 'Alle statischen Tags in Dokumentreihenfolge. parent_index referenziert Index in knoten. Vollständige Attribute, direkte Texte, sichtbare Labels, Links, Formularfelder, Modalstruktur und Initialzustände.'}

DOC['funktionsinventar'] = sorted(FUNCTIONS, key=lambda item: (item['datei'], item['zeile']))
DOC['ui_und_eventinventar'] = {'statisches_dom': UI, 'eventregistrierungen': EVENTS, 'dynamische_operationen': OPERATIONS, 'hinweis': 'Ein Ausdrucksinventar ist ein statischer Index. Alle Callback-Bedingungen und tatsächlichen Reihenfolgen sind in der vollständigen Quelltextreferenz enthalten.'}

css = SOURCE['app/frontend/css/style.css']
DOC['gestaltung'] = {
    'css_variablen': dict(re.findall(r'(--[\w-]+)\s*:\s*([^;]+);', css)),
    'grundprinzipien': ['Heller Hintergrund, weiße Karten, system-ui-Schrift.', 'Violett/Pink für Hauptaktionen, weitere Farbvarianten für Kategorien.', 'Abgerundete Karten, Schatten, zweispaltige Arbeitsbereiche.', 'Scorefarben plus Textwerte; CT-Status eigene Klassen.', 'Ladeindikatoren/Spinner und deaktivierte Aktionen.', 'Responsive Anpassungen über Media Queries.'],
    'media_queries': [{'zeile': css.count('\n', 0, m.start()) + 1, 'query': m.group(1)} for m in re.finditer(r'@media\s*([^\{]+)\{', css)],
    'selektoren_index': [{'zeile': css.count('\n', 0, m.start()) + 1, 'selektor': m.group(1).strip()} for m in re.finditer(r'(?:^|\})\s*([^{}]+)\{', css)],
    'seiteninterne_styles': 'Analyse-Seite hat zusätzlichen style-Block; vollständig im HTML-Quelltext enthalten.',
    'barrierearmut_vorhanden': ['Labels und inputmode numeric', 'aria-live auf einigen Status-/Chatbereichen', 'aria-label auf Fokuscheckboxen und CT-Klärungen', 'Modal role dialog/aria-modal', 'aria-hidden/aria-busy/aria-disabled', 'Escape für mehrere Modals', 'Native details/summary für CT', 'Screenreadertext beim Analyse-Spinner'],
    'keine_auditbehauptung': 'Keine umfassende WCAG-Prüfung; z.B. keine vollständige Modal-Fokusfalle als Feature nachgewiesen.',
    'vollstaendige_css_regeln': 'quelltextreferenz[app/frontend/css/style.css] einschließlich spätere Overrides.'
}
DOC['testinventar'] = {'ausfuehrung': 'run_tests.bat/run_tests.sh -> tests/run_tests.py -> unittest Discovery; Testprotokoll unter outputs.', 'tests': [f for f in FUNCTIONS if f['name'].startswith('test_')], 'pruefung_dieser_dokumentation': 'YAML-Roundtrip, Referenz-/Hash-Prüfung und Abdeckung sämtlicher inventarisierter Funktionen/HTML-Seiten/Prompts; keine Ausführung der Produkt-KI oder Änderung der Anwendung.'}
DOC['batch_labels'] = {p: re.findall(r'^:([^\s]+)', s, re.M) for p, s in SOURCE.items() if p.endswith('.bat')}
DOC['quelltextreferenz'] = {p: {'sha256': hashlib.sha256((ROOT / p).read_bytes()).hexdigest(), 'zeilen': len(s.splitlines()), 'inhalt': s} for p, s in SOURCE.items()}

if UNEXPLAINED:
    raise RuntimeError('Fehlende Funktionsbeschreibungen: ' + ', '.join(UNEXPLAINED))

DOC['inventur_abdeckung'] = {
    'quelldateien': len(FILES), 'html_seiten': len(UI),
    'python_funktionen': sum(f['sprache'] == 'Python' for f in FUNCTIONS),
    'javascript_funktionen': sum(f['sprache'] == 'JavaScript' for f in FUNCTIONS),
    'eventregistrierungen': len(EVENTS), 'statische_dom_knoten': sum(len(x['knoten']) for x in UI.values()),
    'promptdateien': len(DOC['prompting']['vollstaendige_prompts']),
    'regressionstests': len(DOC['testinventar']['tests'])
}

OUT.write_text(yaml.dump(DOC, Dumper=Dumper, allow_unicode=True, sort_keys=False, width=110), encoding='utf-8')
loaded = yaml.safe_load(OUT.read_text(encoding='utf-8'))
assert loaded == DOC, 'YAML-Roundtrip mismatch'
assert len(UI) == 8
assert len(DOC['prompting']['vollstaendige_prompts']) == 4
for path, entry in loaded['quelltextreferenz'].items():
    assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == entry['sha256']
    assert read(path) == entry['inhalt']
for path in FILES:
    if path.endswith('.py'):
        actual = sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) for n in ast.walk(ast.parse(SOURCE[path])))
        assert actual == sum(f['datei'] == path and f['sprache'] == 'Python' for f in FUNCTIONS)
    elif path.endswith(('.html', '.js')):
        assert len(js_function_matches(SOURCE[path])) == sum(f['datei'] == path and f['sprache'] == 'JavaScript' for f in FUNCTIONS)
assert not any(p.endswith('mistral_api_key.txt') or '/data/' in p or p.endswith('.env') for p in FILES)
print(json.dumps({'datei': str(OUT), 'bytes': OUT.stat().st_size, 'zeilen': len(OUT.read_text(encoding='utf-8').splitlines()), 'abdeckung': DOC['inventur_abdeckung'], 'yaml_roundtrip': 'ok', 'quellreferenzen': 'ok'}, ensure_ascii=False))
