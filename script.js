"use strict";

/* =====================================================
   SAHAYAK AI — FRONTEND
===================================================== */

document.addEventListener("DOMContentLoaded", () => {

    const $ = (selector) => document.querySelector(selector);

    const chatView = $("#chatView");
    const adminView = $("#adminView");

    const chatNavButton = $("#chatNavButton");
    const adminNavButton = $("#adminNavButton");

    const pageTitle = $("#pageTitle");
    const sidebar = $("#sidebar");
    const menuToggle = $("#menuToggle");

    const preferencesForm = $("#preferencesForm");
    const studentBranch = $("#studentBranch");
    const studentSemester = $("#studentSemester");
    const savePreferencesButton = $("#savePreferencesButton");
    const preferencesStatus = $("#preferencesStatus");

    const chatForm = $("#chatForm");
    const chatInput = $("#chatInput");
    const chatMessages = $("#chatMessages");
    const sendButton = $("#sendButton");
    const chatStatus = $("#chatStatus");
    const characterCount = $("#characterCount");

    const uploadForm = $("#uploadForm");
    const knowledgeFile = $("#knowledgeFile");
    const selectedFile = $("#selectedFile");
    const uploadButton = $("#uploadButton");
    const uploadStatus = $("#uploadStatus");

    const documentList = $("#documentList");
    const refreshDocumentsButton = $("#refreshDocuments");

    const toast = $("#toast");

    let toastTimeout = null;
    let chatBusy = false;


    /* =================================================
       TOAST NOTIFICATIONS
    ================================================= */

    function showToast(message, isError = false) {

        if (!toast) {
            return;
        }

        toast.textContent = message;

        toast.classList.toggle(
            "toast-error",
            isError
        );

        toast.classList.add("show");

        clearTimeout(toastTimeout);

        toastTimeout = setTimeout(() => {
            toast.classList.remove("show");
        }, 3500);
    }


    /* =================================================
       STATUS MESSAGES
    ================================================= */

    function setStatus(element, message, type = "") {

        if (!element) {
            return;
        }

        element.textContent = message;

        element.classList.remove(
            "success",
            "error"
        );

        if (type) {
            element.classList.add(type);
        }
    }


    /* =================================================
       API HELPER
    ================================================= */

    async function apiRequest(url, options = {}) {

        const response = await fetch(url, {
            credentials: "same-origin",
            ...options
        });

        const contentType = (
            response.headers.get("content-type") || ""
        ).toLowerCase();

        let data = {};

        if (contentType.includes("application/json")) {

            data = await response.json();

        } else {

            if (response.status === 401) {
                throw new Error(
                    "Your login session has expired. Please sign in again."
                );
            }

            throw new Error(
                "The server returned an unexpected response."
            );
        }

        if (response.status === 401) {

            showToast(
                "Your session has expired. Redirecting to login.",
                true
            );

            setTimeout(() => {
                window.location.href = "/login";
            }, 1200);

            throw new Error(
                data.error || "Authentication required."
            );
        }

        if (!response.ok) {

            throw new Error(
                data.error || "The request could not be completed."
            );
        }

        return data;
    }


    /* =================================================
       NAVIGATION
    ================================================= */

    function showView(viewName) {

        if (viewName === "admin" && !adminView) {
            return;
        }

        if (chatView) {
            chatView.classList.toggle(
                "active-view",
                viewName === "chat"
            );
        }

        if (adminView) {
            adminView.classList.toggle(
                "active-view",
                viewName === "admin"
            );
        }

        if (chatNavButton) {
            chatNavButton.classList.toggle(
                "active",
                viewName === "chat"
            );
        }

        if (adminNavButton) {
            adminNavButton.classList.toggle(
                "active",
                viewName === "admin"
            );
        }

        if (pageTitle) {

            pageTitle.textContent = (
                viewName === "admin"
                    ? "Admin Dashboard"
                    : "Student Assistant"
            );
        }

        if (viewName === "admin") {
            loadDocuments();
            loadAdminStats();
        }

        if (sidebar) {
            sidebar.classList.remove("sidebar-open");
        }

        window.scrollTo({
            top: 0,
            behavior: "smooth"
        });
    }


    if (chatNavButton) {

        chatNavButton.addEventListener("click", () => {
            showView("chat");
        });

    }


    if (adminNavButton) {

        adminNavButton.addEventListener("click", () => {
            showView("admin");
        });

    }


    if (menuToggle && sidebar) {

        menuToggle.addEventListener("click", () => {

            sidebar.classList.toggle("sidebar-open");

        });

    }


    document.addEventListener("click", (event) => {

        if (
            sidebar &&
            menuToggle &&
            window.innerWidth <= 850 &&
            sidebar.classList.contains("sidebar-open") &&
            !sidebar.contains(event.target) &&
            !menuToggle.contains(event.target)
        ) {

            sidebar.classList.remove("sidebar-open");

        }

    });


    /* =================================================
       LOAD STUDENT PREFERENCES
    ================================================= */

    async function loadPreferences() {

        if (!preferencesForm) {
            return;
        }

        try {

            const data = await apiRequest(
                "/api/student/preferences"
            );

            if (data.branch) {
                studentBranch.value = data.branch;
            }

            if (data.semester) {
                studentSemester.value = data.semester;
            }

            if (data.branch && data.semester) {

                setStatus(
                    preferencesStatus,
                    `Current profile: ${data.branch}, Semester ${data.semester}`,
                    "success"
                );

            }

        } catch (error) {

            setStatus(
                preferencesStatus,
                error.message,
                "error"
            );

        }

    }


    /* =================================================
       SAVE STUDENT PREFERENCES
    ================================================= */

    if (preferencesForm) {

        preferencesForm.addEventListener(
            "submit",
            async (event) => {

                event.preventDefault();

                const branch = studentBranch.value;
                const semester = studentSemester.value;

                if (!branch || !semester) {

                    setStatus(
                        preferencesStatus,
                        "Please select both branch and semester.",
                        "error"
                    );

                    return;
                }

                savePreferencesButton.disabled = true;

                savePreferencesButton.textContent = "Saving...";

                setStatus(
                    preferencesStatus,
                    "Saving your academic profile..."
                );

                try {

                    const data = await apiRequest(
                        "/api/student/preferences",
                        {
                            method: "POST",

                            headers: {
                                "Content-Type": "application/json"
                            },

                            body: JSON.stringify({
                                branch,
                                semester
                            })
                        }
                    );

                    setStatus(
                        preferencesStatus,
                        data.message ||
                        "Academic profile saved successfully.",
                        "success"
                    );

                    showToast(
                        "Your academic profile has been saved."
                    );

                } catch (error) {

                    setStatus(
                        preferencesStatus,
                        error.message,
                        "error"
                    );

                } finally {

                    savePreferencesButton.disabled = false;

                    savePreferencesButton.textContent =
                        "Save Profile";

                }

            }
        );

    }


    /* =================================================
       CHAT MESSAGE RENDERING
    ================================================= */

    function addMessage(text, sender = "assistant") {

        if (!chatMessages) {
            return;
        }

        const message = document.createElement("div");

        message.className = (
            sender === "user"
                ? "message user-message"
                : "message assistant-message"
        );

        const avatar = document.createElement("div");

        avatar.className = "message-avatar";

        avatar.textContent = (
            sender === "user"
                ? "Y"
                : "S"
        );

        const content = document.createElement("div");

        content.className = "message-content";

        const name = document.createElement("div");

        name.className = "message-name";

        name.textContent = (
            sender === "user"
                ? "You"
                : "SAHAYAK AI"
        );

        const bubble = document.createElement("div");

        bubble.className = "message-bubble";

        /*
         * textContent is intentional.
         * It prevents server responses from being interpreted
         * as HTML, reducing the risk of script injection.
         */
        bubble.textContent = text;

        content.appendChild(name);
        content.appendChild(bubble);

        message.appendChild(avatar);
        message.appendChild(content);

        chatMessages.appendChild(message);

        chatMessages.scrollTop = chatMessages.scrollHeight;

        return message;
    }


    function addTypingIndicator() {

        if (!chatMessages) {
            return null;
        }

        const indicator = document.createElement("div");

        indicator.className = "typing-indicator";

        indicator.textContent = "SAHAYAK AI is searching...";

        chatMessages.appendChild(indicator);

        chatMessages.scrollTop = chatMessages.scrollHeight;

        return indicator;
    }


    /* =================================================
       SEND CHAT MESSAGE
    ================================================= */

    async function sendMessage(message) {

        const text = String(message || "").trim();

        if (!text || chatBusy) {
            return;
        }

        if (text.length > 2000) {

            setStatus(
                chatStatus,
                "Please keep your question within 2000 characters.",
                "error"
            );

            return;
        }

        chatBusy = true;

        if (chatInput) {
            chatInput.value = "";
            updateCharacterCount();
        }

        if (sendButton) {
            sendButton.disabled = true;
        }

        setStatus(chatStatus, "");

        addMessage(text, "user");

        const typingIndicator = addTypingIndicator();

        try {

            const data = await apiRequest(
                "/api/chat",
                {
                    method: "POST",

                    headers: {
                        "Content-Type": "application/json"
                    },

                    body: JSON.stringify({
                        message: text
                    })
                }
            );

            if (typingIndicator) {
                typingIndicator.remove();
            }

            if (data.needs_preferences) {

                addMessage(
                    data.reply ||
                    "Please save your branch and semester first.",
                    "assistant"
                );

                if (preferencesForm) {

                    preferencesForm.scrollIntoView({
                        behavior: "smooth",
                        block: "center"
                    });

                }

                return;
            }

            addMessage(
                data.reply ||
                "The server did not return an answer.",
                "assistant"
            );

        } catch (error) {

            if (typingIndicator) {
                typingIndicator.remove();
            }

            addMessage(
                "Sorry, I couldn't process your question. " +
                error.message,
                "assistant"
            );

        } finally {

            chatBusy = false;

            if (sendButton) {
                sendButton.disabled = false;
            }

            if (chatInput) {
                chatInput.focus();
            }

        }

    }


    /* =================================================
       CHAT FORM
    ================================================= */

    if (chatForm) {

        chatForm.addEventListener(
            "submit",
            (event) => {

                event.preventDefault();

                sendMessage(chatInput.value);

            }
        );

    }


    /* =================================================
       CHARACTER COUNTER
    ================================================= */

    function updateCharacterCount() {

        if (!chatInput || !characterCount) {
            return;
        }

        characterCount.textContent =
            `${chatInput.value.length} / 2000`;

    }


    if (chatInput) {

        chatInput.addEventListener(
            "input",
            updateCharacterCount
        );

        chatInput.addEventListener(
            "keydown",
            (event) => {

                if (
                    event.key === "Enter" &&
                    !event.shiftKey &&
                    !event.isComposing
                ) {

                    event.preventDefault();

                    if (chatForm) {
                        chatForm.requestSubmit();
                    }

                }

            }
        );

    }


    /* =================================================
       QUICK QUESTION BUTTONS
    ================================================= */

    document.querySelectorAll(
        "[data-question]"
    ).forEach((button) => {

        button.addEventListener("click", () => {

            const question = button.dataset.question;

            showView("chat");

            sendMessage(question);

        });

    });


    /* =================================================
       FILE SELECTION
    ================================================= */

    if (knowledgeFile) {

        knowledgeFile.addEventListener(
            "change",
            () => {

                const file = knowledgeFile.files[0];

                if (!file) {

                    selectedFile.textContent =
                        "No file selected";

                    return;
                }

                selectedFile.textContent =
                    `${file.name} (${formatBytes(file.size)})`;

                setStatus(uploadStatus, "");

            }
        );

    }


    function formatBytes(bytes) {

        if (bytes < 1024) {
            return `${bytes} B`;
        }

        if (bytes < 1024 * 1024) {
            return `${(bytes / 1024).toFixed(1)} KB`;
        }

        return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;

    }


    /* =================================================
       DRAG AND DROP
    ================================================= */

    const dropZone = $("#dropZone");

    if (dropZone && knowledgeFile) {

        ["dragenter", "dragover"].forEach((eventName) => {

            dropZone.addEventListener(eventName, (event) => {

                event.preventDefault();

                dropZone.classList.add("drag-over");

            });

        });


        ["dragleave", "drop"].forEach((eventName) => {

            dropZone.addEventListener(eventName, (event) => {

                event.preventDefault();

                dropZone.classList.remove("drag-over");

            });

        });


        dropZone.addEventListener("drop", (event) => {

            const files = event.dataTransfer.files;

            if (!files || !files.length) {
                return;
            }

            try {

                const transfer = new DataTransfer();

                transfer.items.add(files[0]);

                knowledgeFile.files = transfer.files;

                knowledgeFile.dispatchEvent(
                    new Event("change", { bubbles: true })
                );

            } catch (error) {

                showToast(
                    "Please use Browse Files to select your document.",
                    true
                );

            }

        });

    }


    /* =================================================
       UPLOAD DOCUMENT
    ================================================= */

    if (uploadForm) {

        uploadForm.addEventListener(
            "submit",
            async (event) => {

                event.preventDefault();

                const file = knowledgeFile.files[0];

                if (!file) {

                    setStatus(
                        uploadStatus,
                        "Please select a document first.",
                        "error"
                    );

                    return;
                }

                if (file.size > 8 * 1024 * 1024) {

                    setStatus(
                        uploadStatus,
                        "The file must be 8 MB or smaller.",
                        "error"
                    );

                    return;
                }

                const allowedExtensions = [
                    "pdf",
                    "txt",
                    "md",
                    "csv",
                    "docx",
                    "xlsx"
                ];

                const extension = file.name
                    .split(".")
                    .pop()
                    .toLowerCase();

                if (!allowedExtensions.includes(extension)) {

                    setStatus(
                        uploadStatus,
                        "This file format is not supported.",
                        "error"
                    );

                    return;
                }

                const formData = new FormData(uploadForm);

                uploadButton.disabled = true;

                uploadButton.textContent = "Uploading...";

                setStatus(
                    uploadStatus,
                    "Uploading and extracting document text..."
                );

                try {

                    const data = await apiRequest(
                        "/api/admin/documents",
                        {
                            method: "POST",
                            body: formData
                        }
                    );

                    setStatus(
                        uploadStatus,
                        data.message ||
                        "Document uploaded successfully.",
                        "success"
                    );

                    showToast(
                        "Document uploaded successfully."
                    );

                    uploadForm.reset();

                    selectedFile.textContent =
                        "No file selected";

                    await loadDocuments();

                    await loadAdminStats();

                } catch (error) {

                    setStatus(
                        uploadStatus,
                        error.message,
                        "error"
                    );

                } finally {

                    uploadButton.disabled = false;

                    uploadButton.textContent =
                        "Upload Document";

                }

            }
        );

    }


    /* =================================================
       LOAD DOCUMENT LIST
    ================================================= */

    async function loadDocuments() {

        if (!documentList) {
            return;
        }

        documentList.replaceChildren();

        const loading = document.createElement("div");

        loading.className = "empty-state";

        loading.textContent = "Loading documents...";

        documentList.appendChild(loading);

        try {

            const data = await apiRequest(
                "/api/admin/documents"
            );

            const documents = data.documents || [];

            documentList.replaceChildren();

            if (documents.length === 0) {

                const empty = document.createElement("div");

                empty.className = "empty-state";

                empty.textContent =
                    "No knowledge documents have been uploaded yet.";

                documentList.appendChild(empty);

                updateDocumentStats([]);

                return;
            }

            documents.forEach((doc) => {

                const item = document.createElement("article");

                item.className = "document-item";

                const icon = document.createElement("div");

                icon.className = "document-icon";

                icon.textContent = getFileIcon(
                    doc.filename
                );

                const info = document.createElement("div");

                info.className = "document-info";

                const title = document.createElement("h4");

                title.textContent = doc.filename;

                const details = document.createElement("p");

                details.textContent =
                    `${formatNumber(doc.characters || 0)} characters` +
                    ` · Uploaded ${doc.uploaded_at || "date unavailable"}`;

                const tags = document.createElement("div");

                tags.className = "document-tags";

                const branchTag = document.createElement("span");

                branchTag.className = "document-tag";

                branchTag.textContent =
                    `Branch: ${doc.branch || "ALL"}`;

                const semesterTag = document.createElement("span");

                semesterTag.className = "document-tag";

                semesterTag.textContent =
                    `Semester: ${doc.semester || "ALL"}`;

                tags.appendChild(branchTag);
                tags.appendChild(semesterTag);

                info.appendChild(title);
                info.appendChild(details);
                info.appendChild(tags);

                const deleteButton =
                    document.createElement("button");

                deleteButton.type = "button";

                deleteButton.className =
                    "delete-document-button";

                deleteButton.textContent = "Delete";

                deleteButton.addEventListener(
                    "click",
                    () => deleteDocument(
                        doc.id,
                        doc.filename
                    )
                );

                item.appendChild(icon);
                item.appendChild(info);
                item.appendChild(deleteButton);

                documentList.appendChild(item);

            });

            updateDocumentStats(documents);

        } catch (error) {

            documentList.replaceChildren();

            const errorBox = document.createElement("div");

            errorBox.className = "empty-state";

            errorBox.textContent =
                `Could not load documents: ${error.message}`;

            documentList.appendChild(errorBox);

        }

    }


    /* =================================================
       FILE ICON
    ================================================= */

    function getFileIcon(filename) {

        const extension = (
            filename.split(".").pop() || ""
        ).toLowerCase();

        const icons = {
            pdf: "📕",
            docx: "📘",
            txt: "📄",
            md: "📝",
            csv: "📊",
            xlsx: "📗"
        };

        return icons[extension] || "📁";

    }


    /* =================================================
       DOCUMENT STATISTICS
    ================================================= */

    function updateDocumentStats(documents) {

        const docCount = $("#docCount");

        const charCount = $("#charCount");

        if (docCount) {

            docCount.textContent =
                formatNumber(documents.length);

        }

        if (charCount) {

            const totalCharacters = documents.reduce(
                (total, doc) => {
                    return total + Number(
                        doc.characters || 0
                    );
                },
                0
            );

            charCount.textContent =
                formatNumber(totalCharacters);

        }

    }


    /* =================================================
       DELETE DOCUMENT
    ================================================= */

    async function deleteDocument(id, filename) {

        const confirmed = window.confirm(
            `Delete "${filename}" from the knowledge library?`
        );

        if (!confirmed) {
            return;
        }

        try {

            const data = await apiRequest(
                `/api/admin/documents/${encodeURIComponent(id)}`,
                {
                    method: "DELETE"
                }
            );

            showToast(
                data.message || "Document deleted."
            );

            await loadDocuments();

            await loadAdminStats();

        } catch (error) {

            showToast(
                error.message,
                true
            );

        }

    }


    /* =================================================
       ADMIN DATABASE STATISTICS
    ================================================= */

    async function loadAdminStats() {

        const databaseStats = $("#databaseStats");

        if (!databaseStats) {
            return;
        }

        databaseStats.textContent =
            "Loading statistics...";

        try {

            const data = await apiRequest(
                "/api/admin/data"
            );

            const counts = data.counts || {};

            databaseStats.replaceChildren();

            const labels = {
                courses: "Courses",
                timetable: "Timetable Records",
                exam_dates: "Exam Records",
                fees: "Fee Records",
                library_timings: "Library Records",
                hostel: "Hostel Records",
                scholarships: "Scholarships",
                knowledge_documents: "Knowledge Documents",
                student_preferences: "Student Profiles"
            };

            Object.entries(labels).forEach(
                ([key, label]) => {

                    const card = document.createElement("div");

                    card.className = "database-stat";

                    const title = document.createElement("span");

                    title.textContent = label;

                    const value = document.createElement("strong");

                    value.textContent = formatNumber(
                        counts[key] || 0
                    );

                    card.appendChild(title);
                    card.appendChild(value);

                    databaseStats.appendChild(card);

                }
            );

            const courseCount = $("#courseCount");

            const studentCount = $("#studentCount");

            if (courseCount) {

                courseCount.textContent = formatNumber(
                    counts.courses || 0
                );

            }

            if (studentCount) {

                studentCount.textContent = formatNumber(
                    counts.student_preferences || 0
                );

            }

        } catch (error) {

            databaseStats.textContent =
                `Could not load statistics: ${error.message}`;

        }

    }


    /* =================================================
       NUMBER FORMATTING
    ================================================= */

    function formatNumber(value) {

        return Number(value || 0).toLocaleString("en-IN");

    }


    /* =================================================
       REFRESH BUTTON
    ================================================= */

    if (refreshDocumentsButton) {

        refreshDocumentsButton.addEventListener(
            "click",
            async () => {

                refreshDocumentsButton.disabled = true;

                refreshDocumentsButton.textContent =
                    "Refreshing...";

                await loadDocuments();

                await loadAdminStats();

                refreshDocumentsButton.disabled = false;

                refreshDocumentsButton.textContent =
                    "↻ Refresh";

                showToast(
                    "Dashboard refreshed."
                );

            }
        );

    }


    /* =================================================
       INITIALIZATION
    ================================================= */

    loadPreferences();

    updateCharacterCount();

    if (adminView && adminView.classList.contains("active-view")) {

        loadDocuments();

        loadAdminStats();

    }

});