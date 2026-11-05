// ==========================================
// GET HTML ELEMENTS
// ==========================================

const fileInput = document.getElementById("fileInput");

const uploadBox = document.getElementById("uploadBox");

const chooseFile = document.getElementById("chooseFile");

const replaceFile = document.getElementById("replaceFile");

const selectedFileView =
    document.getElementById("selectedFileView");

const fileName =
    document.getElementById("fileName");

const fileSize =
    document.getElementById("fileSize");

const fileStatus =
    document.getElementById("fileStatus");

const startAnalysis =
    document.getElementById("startAnalysis");

const uploadMessage =
    document.getElementById("uploadMessage");

const analysisDashboard =
    document.getElementById("analysisDashboard");

const dashboardFilename =
    document.getElementById("dashboardFilename");

const documentContent =
    document.getElementById("documentContent");

const backToUpload =
    document.getElementById("backToUpload");

const analysisTabs = document.querySelector(".analysis-tabs");
const newAnalysisTab = document.getElementById("new-analysis-tab");
const existingAnalysisTab = document.getElementById("existing-analysis-tab");
const newAnalysisPanel = document.getElementById("new-analysis-panel");
const existingAnalysisPanel = document.getElementById("existing-analysis-panel");
const analysisHistoryElement = document.getElementById("analysisHistory");
const timelineDialog = document.getElementById("timelineDialog");
const historyTabs = [document.getElementById("eventsTab"), document.getElementById("sessionsTab")];
function showHistoryTab(index) {
    historyTabs.forEach(function (tab, position) {
        tab.setAttribute("aria-selected", String(position === index));
        tab.tabIndex = position === index ? 0 : -1;
        document.getElementById(tab.getAttribute("aria-controls")).hidden = position !== index;
    });
}
historyTabs.forEach(function (tab, index) {
    tab.addEventListener("click", function () { showHistoryTab(index); });
    tab.addEventListener("keydown", function (event) {
        let next;
        if (event.key === "ArrowLeft" || event.key === "ArrowRight") next = 1 - index;
        if (event.key === "Home") next = 0;
        if (event.key === "End") next = 1;
        if (next !== undefined) {
            event.preventDefault();
            showHistoryTab(next);
            historyTabs[next].focus();
        }
    });
});
const metadataPanel = document.getElementById("paragraphMetadata");
const writingPanel = document.getElementById("writingStyle");
const paragraphSelection = document.getElementById("paragraphSelection");
const detailTabs = [document.getElementById("metadataTab"), document.getElementById("writingTab")];
let documentReadVersion = 0;
let currentAnalysis = null;

function renderDocumentAnalysis(result) {
    renderDocumentHistory(result);
    const metrics = result.metrics;
    const value = item => item == null ? "Not available" : String(item);
    document.getElementById("timelineSha256").textContent = "SHA-256: " + value(result.sha256);
    renderParagraphFacts(document.getElementById("documentSummary"), [
        ["Root RSID", value(result.rsid_root)],
        ["Total words", value(metrics.total_word_count)],
        ["Recorded revision count", value(metrics.revision_count)],
        ["Unique paragraph RSIDs", value(metrics.unique_rsid_count)],
        ["Words / recorded revision", value(metrics.word_to_revision_ratio)],
        ["Paragraph RSIDs / recorded revision", value(metrics.unique_rsid_to_revision_ratio)]
    ]);
    document.getElementById("documentChecks").textContent =
        "Working copy integrity: " + (result.integrity_verified ? "Verified" : "Not verified") +
        ". Validation warnings: " + ((result.warnings || []).join("; ") || "None");
    const rankings = document.getElementById("sessionRankings");
    if (result.top_sessions.length) {
        renderParagraphFacts(rankings, result.top_sessions.map(group => [
            group.rsid + " (" + group.session_type + ")", group.word_count + " words"
        ]));
    } else rankings.textContent = "No paragraph RSIDs recorded in this document.";
}

function setHistoryMessage(message) {
    for (const id of ["timelineEvents", "editingSessions"]) {
        document.getElementById(id).textContent = message;
    }
}

function appendHistoryCard(panel, title, detail) {
    const card = document.createElement("details");
    card.className = "history-card";
    const summary = document.createElement("summary");
    const label = document.createElement("strong");
    label.textContent = title;
    summary.append(label);
    const text = document.createElement("p");
    text.textContent = detail;
    card.append(summary, text);
    panel.append(card);
}

function renderDocumentHistory(result) {
    const events = document.getElementById("timelineEvents");
    const sessions = document.getElementById("editingSessions");
    events.replaceChildren();
    sessions.replaceChildren();
    const timeline = document.createElement("ol");
    timeline.className = "document-timeline";
    // Backend metadata fields: creator and last_modified_by (DOCX core properties).
    for (const [label, date, authorLabel, author] of [
        ["Document Created", result.metadata.creation_date, "Created by", result.metadata.creator],
        ["Document Modified", result.metadata.modified_date, "Modified by", result.metadata.last_modified_by]
    ]) {
        if (!date) continue;
        const item = document.createElement("li");
        const timestamp = document.createElement("time");
        timestamp.dateTime = date;
        timestamp.textContent = date;
        const description = document.createElement("p");
        description.textContent = label;
        const attribution = document.createElement("p");
        attribution.className = "timeline-author";
        attribution.textContent = authorLabel + ": " +
            (typeof author === "string" && author.trim() ? author.trim() : "Not available");
        item.append(timestamp, description, attribution);
        timeline.append(item);
    }
    if (timeline.childElementCount) {
        events.append(timeline);
    } else {
        events.textContent = "No document dates were returned by the backend.";
    }
    const groups = Object.entries(result.metrics.session_word_aggregates);
    groups.sort((a, b) => b[1] - a[1]);
    for (const [rsid, words] of groups) {
        const groupType = result.metrics.session_types[rsid];
        appendHistoryCard(sessions, "RSID " + rsid,
            words + " associated words" + (groupType ? " · " + groupType : "") +
            ". Edit timestamp unavailable.");
    }
    if (!groups.length) sessions.textContent = "No paragraph RSID groups were returned by the backend.";
}

function showDetailTab(index) {
    detailTabs.forEach(function (tab, tabIndex) {
        tab.setAttribute("aria-selected", String(tabIndex === index));
        tab.tabIndex = tabIndex === index ? 0 : -1;
    });
    metadataPanel.hidden = index !== 0;
    writingPanel.hidden = index !== 1;
}

detailTabs.forEach(function (tab, index) {
    tab.addEventListener("click", function () { showDetailTab(index); });
    tab.addEventListener("keydown", function (event) {
        let next;
        if (event.key === "ArrowRight" || event.key === "ArrowLeft") next = 1 - index;
        if (event.key === "Home") next = 0;
        if (event.key === "End") next = 1;
        if (next !== undefined) {
            event.preventDefault();
            showDetailTab(next);
            detailTabs[next].focus();
        }
    });
});

function renderParagraphFacts(panel, facts) {
    const list = document.createElement("dl");
    list.className = "paragraph-facts";
    facts.forEach(function ([label, value]) {
        const row = document.createElement("div");
        const term = document.createElement("dt");
        const description = document.createElement("dd");
        term.textContent = label;
        description.textContent = value;
        row.append(term, description);
        list.append(row);
    });
    panel.replaceChildren(list);
}

function selectParagraph(paragraph) {
    documentContent.querySelectorAll(".interactive-paragraph").forEach(function (item) {
        item.classList.toggle("is-selected", item === paragraph);
        item.setAttribute("aria-pressed", String(item === paragraph));
    });
    const text = paragraph.textContent.trim();
    const words = text.match(/\S+/g) || [];
    const sentences = text.match(/[^.!?]+[.!?]+|[^.!?]+$/g) || [];
    const average = words.length / Math.max(sentences.length, 1);
    const details = currentAnalysis?.paragraphs[Number(paragraph.dataset.analysisIndex)];
    paragraphSelection.textContent = "Paragraph " + paragraph.dataset.paragraphNumber;
    renderParagraphFacts(metadataPanel, [
        ["Paragraph RSID", details?.paragraph_rsidR || "Not recorded"],
        ["Default RSID", details?.paragraph_rsidDefault || "Not recorded"],
        ["RSID group", details?.session_type || "Unknown"],
        ["Text run RSIDs", [...new Set((details?.runs || []).map(run => run.rsidR).filter(Boolean))].join(", ") || "Not recorded"]
    ]);
    renderParagraphFacts(writingPanel, [
        ["Word count", String(details?.word_count ?? words.length)],
        ["Sentence count (estimated)", String(sentences.length)],
        ["Average sentence length", average.toFixed(1) + " words"],
        ["Characters (including spaces)", String(text.length)]
    ]);
    const insight = document.createElement("p");
    insight.className = "paragraph-hint";
    insight.textContent = average > 25
        ? "This paragraph uses long sentences on average. Consider splitting longer sentences to improve readability."
        : "This paragraph uses " + (average > 15 ? "moderate-length" : "short") + " sentences on average.";
    writingPanel.append(insight);
}

function enableParagraphSelection() {
    const rsidColours = new Map();
    documentContent.querySelectorAll(".rsid-run").forEach(function (run) {
        const rsid = run.dataset.rsid.trim().toUpperCase();
        if (!rsid) {
            run.title = "Text RSID not recorded";
            return;
        }
        if (!rsidColours.has(rsid)) {
            // Generate additional colours instead of cycling a fixed palette.
            const hue = (rsidColours.size * 137.508 + 30) % 360;
            rsidColours.set(rsid, "hsl(" + hue + ", 70%, 82%)");
        }
        run.style.backgroundColor = rsidColours.get(rsid);
        run.title = "Text RSID: " + rsid;
    });
    const paragraphs = Array.from(documentContent.querySelectorAll("p"))
        .filter(function (paragraph) { return paragraph.textContent.trim(); });
    paragraphs.forEach(function (paragraph, index) {
        paragraph.classList.add("interactive-paragraph");
        paragraph.dataset.paragraphNumber = String(index + 1);
        paragraph.tabIndex = 0;
        paragraph.setAttribute("role", "button");
        paragraph.setAttribute("aria-pressed", "false");
        paragraph.setAttribute("aria-label", "View details for paragraph " + (index + 1) + ": " + paragraph.textContent.trim());
        paragraph.addEventListener("click", function (event) {
            if (event.target.closest("a")) return;
            selectParagraph(paragraph);
        });
        paragraph.addEventListener("keydown", function (event) {
            if (event.target !== paragraph) return;
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                selectParagraph(paragraph);
            }
        });
    });
    if (paragraphs.length) selectParagraph(paragraphs[0]);
    else paragraphSelection.textContent = "No text paragraphs are available in this document.";
}

document.getElementById("viewTimeline").addEventListener("click", function () {
    showHistoryTab(0);
    document.getElementById("timelineFilename").textContent = dashboardFilename.textContent;
    timelineDialog.showModal();
});

document.getElementById("closeTimeline").addEventListener("click", function () {
    timelineDialog.close();
});

timelineDialog.addEventListener("click", function (event) {
    const bounds = timelineDialog.getBoundingClientRect();
    if (event.target === timelineDialog &&
        (event.clientX < bounds.left || event.clientX > bounds.right ||
         event.clientY < bounds.top || event.clientY > bounds.bottom)) {
        timelineDialog.close();
    }
});


// Store the selected file
let selectedFile = null;
let analysisHistory = [];

async function refreshSavedAnalyses() {
    try {
        if (!window.pywebview?.api) return;
        const response = await window.pywebview.api.list_sessions();
        if (!response.success) throw new Error(response.message);
        analysisHistory = response.sessions;
        renderAnalysisHistory();
        if (!analysisHistory.length) analysisHistoryElement.textContent = "No saved analyses yet.";
    } catch (error) {
        analysisHistoryElement.textContent = error.message;
    }
}

window.addEventListener("pywebviewready", refreshSavedAnalyses);


function renderAnalysisHistory() {

    analysisHistoryElement.replaceChildren();

    analysisHistory.forEach(function (file, index) {

        const item = document.createElement("div");
        item.className = "analysis-history-item";

        const name = document.createElement("span");
        name.className = "analysis-history-name";
        name.textContent = file.name;

        const openButton = document.createElement("button");
        openButton.type = "button";
        openButton.className = "upload-btn analysis-history-open";
        openButton.dataset.analysisIndex = String(index);
        openButton.textContent = "Open Analysis";

        const actions = document.createElement("div");
        actions.className = "analysis-history-actions";
        const deleteButton = document.createElement("button");
        deleteButton.type = "button";
        deleteButton.className = "analysis-history-delete";
        deleteButton.setAttribute("aria-label", "Delete saved analysis for " + file.name);
        deleteButton.title = "Delete saved analysis";
        deleteButton.innerHTML = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7"/></svg>';
        deleteButton.addEventListener("click", async function () {
            const status = document.getElementById("analysisHistoryStatus");
            status.hidden = true;
            deleteButton.disabled = true;
            openButton.disabled = true;
            try {
                // Future backend contract: delete_analysis(session_id) -> {success, message?}.
                if (typeof window.pywebview?.api?.delete_analysis !== "function") {
                    throw new Error("Deleting saved analyses is not available yet.");
                }
                const response = await window.pywebview.api.delete_analysis(file.id);
                if (!response.success) throw new Error(response.message || "Unable to delete saved analysis.");
                await refreshSavedAnalyses();
            } catch (error) {
                status.textContent = error.message;
                status.hidden = false;
            } finally {
                deleteButton.disabled = false;
                openButton.disabled = false;
            }
        });
        actions.append(openButton, deleteButton);
        item.append(name, actions);
        analysisHistoryElement.append(item);

    });

}


function openAnalysis(file) {

    selectedFile = file;
    dashboardFilename.textContent = file.name;
    dashboardFilename.hidden = false;
    document.getElementById("viewTimeline").hidden = false;
    document.getElementById("exportFullAnalysis").hidden = false;
    newAnalysisPanel.hidden = true;
    existingAnalysisPanel.hidden = true;
    analysisTabs.hidden = true;
    analysisDashboard.hidden = false;
    document.querySelector(".main-container").classList.add("dashboard-mode");
    readDocument(file, file.id);

}


analysisHistoryElement.addEventListener("click", function (event) {

    const button = event.target.closest("[data-analysis-index]");

    if (button) {
        openAnalysis(analysisHistory[Number(button.dataset.analysisIndex)]);
    }

});


// ==========================================
// ANALYSIS TABS
// ==========================================

function showTab(tab, panel) {

    newAnalysisTab.classList.toggle("active", tab === newAnalysisTab);
    existingAnalysisTab.classList.toggle("active", tab === existingAnalysisTab);
    newAnalysisPanel.hidden = panel !== newAnalysisPanel;
    existingAnalysisPanel.hidden = panel !== existingAnalysisPanel;

}


newAnalysisTab.addEventListener("click", function () {

    showTab(newAnalysisTab, newAnalysisPanel);

});


existingAnalysisTab.addEventListener("click", function () {

    showTab(existingAnalysisTab, existingAnalysisPanel);
    refreshSavedAnalyses();

});


// ==========================================
// OPEN FILE SELECTOR
// ==========================================

chooseFile.addEventListener("click", function () {

    fileInput.click();

});


replaceFile.addEventListener("click", function () {

    fileInput.value = "";

    fileInput.click();

});


// ==========================================
// USER SELECTS FILE
// ==========================================

fileInput.addEventListener("change", function () {

    const file = fileInput.files[0];

    if (file) {

        selectFile(file);

    }

});


// ==========================================
// SELECT FILE FUNCTION
// ==========================================

function selectFile(file) {

    // File validation is performed by the backend when analysis starts.
    selectedFile = null;
    fileName.textContent = file.name;

    if (file.size < 1024 * 1024) {
        fileSize.textContent = (file.size / 1024).toFixed(1) + " KB";
    } else {
        fileSize.textContent = (file.size / (1024 * 1024)).toFixed(1) + " MB";
    }

    uploadBox.hidden = true;
    selectedFileView.hidden = false;
    uploadMessage.hidden = true;

    selectedFile = file;
    fileStatus.textContent = "\u2713 File selected successfully";
    fileStatus.classList.remove("is-error");
    startAnalysis.hidden = false;
}

// ==========================================
// DRAG AND DROP
// ==========================================

uploadBox.addEventListener("dragover", function (event) {

    event.preventDefault();

    uploadBox.classList.add("is-dragging");

});


uploadBox.addEventListener("dragleave", function () {

    uploadBox.classList.remove("is-dragging");

});


uploadBox.addEventListener("drop", function (event) {

    event.preventDefault();

    uploadBox.classList.remove("is-dragging");


    const files = event.dataTransfer.files;


    if (files.length !== 1) {

        uploadMessage.textContent =
            "Please choose one document at a time.";

        uploadMessage.hidden = false;

        return;

    }


    selectFile(files[0]);

});


// ==========================================
// START ANALYSIS
// ==========================================

startAnalysis.addEventListener("click", function () {

    if (!selectedFile) {

        return;

    }


    openAnalysis(selectedFile);

});


// ==========================================
// READ DOCUMENT
// ==========================================

async function readDocument(file, sessionId) {
    const readVersion = ++documentReadVersion;
    currentAnalysis = null;
    document.getElementById("timelineSha256").textContent = "";
    document.getElementById("documentChecks").textContent = "";
    document.getElementById("exportFullAnalysis").disabled = true;
    document.getElementById("analysisActionStatus").textContent = "";
    setHistoryMessage("Reading document analysis...");
    document.getElementById("documentSummary").textContent = "Reading metadata...";
    document.getElementById("sessionRankings").replaceChildren();
    showDetailTab(0);
    paragraphSelection.textContent = "Select a highlighted paragraph to view its details.";
    metadataPanel.textContent = "Paragraph metadata will appear here.";
    writingPanel.textContent = "Select a highlighted paragraph to view its writing analysis.";
    documentContent.textContent = "Reading document...";
    try {
        if (!window.pywebview?.api) throw new Error("Open the desktop app with main.py to analyse documents.");
        let result;
        if (sessionId) {
            result = await window.pywebview.api.load_analysis(sessionId);
        } else {
            const encoded = await new Promise(function (resolve, reject) {
                const reader = new FileReader();
                reader.onload = () => resolve(reader.result.split(",")[1]);
                reader.onerror = () => reject(new Error("Unable to read the selected file."));
                reader.readAsDataURL(file);
            });
            if (readVersion !== documentReadVersion) return;
            result = await window.pywebview.api.read_docx(file.name, encoded);
        }
        if (readVersion !== documentReadVersion) return;
        if (!result.success) throw new Error(result.message);
        currentAnalysis = result;
        document.getElementById("exportFullAnalysis").disabled = !result.session_id;
        document.getElementById("analysisActionStatus").textContent = result.storage_error || "";
        renderDocumentAnalysis(result);
        documentContent.innerHTML = result.html;
        enableParagraphSelection();
        refreshSavedAnalyses();
    } catch (error) {
        if (readVersion === documentReadVersion) {
            documentContent.textContent = error.message;
            document.getElementById("documentSummary").textContent = "Analysis unavailable.";
            setHistoryMessage("Analysis unavailable for this file.");
        }
    }
}

document.getElementById("exportFullAnalysis").addEventListener("click", async function () {
    if (!currentAnalysis?.session_id) return;
    const button = this;
    const status = document.getElementById("analysisActionStatus");
    const version = documentReadVersion;
    button.disabled = true;
    try {
        const response = await window.pywebview.api.export_analysis(currentAnalysis.session_id);
        if (version !== documentReadVersion) return;
        if (!response.success) throw new Error(response.message);
        status.textContent = response.cancelled ? "Export cancelled." : "";
    } catch (error) {
        if (version === documentReadVersion) status.textContent = error.message;
    } finally {
        if (version === documentReadVersion) button.disabled = !currentAnalysis?.session_id;
    }
});

// ==========================================
// BACK TO UPLOAD
// ==========================================

backToUpload.addEventListener("click", function () {
    documentReadVersion++;

    analysisDashboard.hidden = true;
    dashboardFilename.hidden = true;
    document.getElementById("viewTimeline").hidden = true;
    document.getElementById("exportFullAnalysis").hidden = true;
    document.querySelector(".main-container").classList.remove("dashboard-mode");

    selectedFile = null;
    fileInput.value = "";
    fileName.textContent = "";
    fileSize.textContent = "";
    fileStatus.textContent = "\u2713 File selected successfully";
    fileStatus.classList.remove("is-error");
    startAnalysis.hidden = true;
    selectedFileView.hidden = true;
    uploadBox.hidden = false;
    uploadMessage.hidden = true;

    analysisTabs.hidden = false;
    showTab(newAnalysisTab, newAnalysisPanel);


    document.getElementById(
        "new-analysis-panel"
    ).hidden = false;

});

