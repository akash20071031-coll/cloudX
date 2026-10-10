const API_BASE = "http://127.0.0.1:8000";


// ============================================================
// LOAD DASHBOARD
// ============================================================

async function loadDashboard() {

    await loadEvidence();

}


// ============================================================
// LOAD EVIDENCE
// ============================================================

async function loadEvidence() {

    try {

        const response = await fetch(
            `${API_BASE}/api/artefacts`
        );

        if (!response.ok) {
            throw new Error("Failed to load evidence");
        }

        const data = await response.json();

        const evidence = data.artefacts || [];

        // Statistics

        document.getElementById(
            "totalEvidence"
        ).textContent = evidence.length;


        const verified = evidence.filter(
            item => item.status === "VERIFIED"
        ).length;


        const tampered = evidence.filter(
            item => item.status === "TAMPERED"
        ).length;


        document.getElementById(
            "verifiedEvidence"
        ).textContent = verified;


        document.getElementById(
            "tamperedEvidence"
        ).textContent = tampered;


        // Table

        const table =
            document.getElementById(
                "evidenceTable"
            );


        if (evidence.length === 0) {

            table.innerHTML = `
                <tr>
                    <td colspan="6" class="loading">
                        No evidence collected yet.
                    </td>
                </tr>
            `;

            return;
        }


        table.innerHTML = evidence
            .slice(0, 10)
            .map(item => {

                const statusClass =
                    item.status.toLowerCase();


                return `
                    <tr>

                        <td>
                            <strong>
                                ${item.evidence_id}
                            </strong>
                        </td>

                        <td>
                            ${escapeHtml(item.filename)}
                        </td>

                        <td class="hash">
                            ${item.sha256.substring(0, 18)}...
                        </td>

                        <td>

                            <span class="badge ${statusClass}">
                                ${item.status}
                            </span>

                        </td>

                        <td>
                            ${escapeHtml(item.uploaded_by)}
                        </td>

                        <td>
                            ${formatDate(item.uploaded_at)}
                        </td>

                    </tr>
                `;

            })
            .join("");

    }

    catch (error) {

        console.error(error);

        document.getElementById(
            "evidenceTable"
        ).innerHTML = `
            <tr>
                <td colspan="6" class="loading">
                    Unable to connect to SecureX backend.
                </td>
            </tr>
        `;

    }

}


// ============================================================
// OPEN UPLOAD
// ============================================================

function openUpload() {

    document
        .getElementById("uploadModal")
        .classList
        .add("show");

}


// ============================================================
// CLOSE UPLOAD
// ============================================================

function closeUpload() {

    document
        .getElementById("uploadModal")
        .classList
        .remove("show");

}


// ============================================================
// UPLOAD EVIDENCE
// ============================================================

async function uploadEvidence(event) {

    event.preventDefault();


    const fileInput =
        document.getElementById(
            "evidenceFile"
        );


    const result =
        document.getElementById(
            "uploadResult"
        );


    if (!fileInput.files.length) {

        result.textContent =
            "Please select a file.";

        return;
    }


    const formData =
        new FormData();


    formData.append(
        "file",
        fileInput.files[0]
    );


    result.textContent =
        "Uploading and calculating SHA-256...";


    try {

        const response = await fetch(
            `${API_BASE}/api/ingest`,
            {
                method: "POST",
                body: formData
            }
        );


        const data =
            await response.json();


        if (!response.ok) {
            throw new Error(
                data.detail || "Upload failed"
            );
        }


        result.innerHTML = `
            <strong>Evidence securely ingested.</strong><br>
            Evidence ID: ${data.evidence_id}<br>
            SHA-256:
            ${data.sha256}
        `;


        fileInput.value = "";


        await loadEvidence();


        setTimeout(
            closeUpload,
            2500
        );

    }

    catch (error) {

        result.textContent =
            `Error: ${error.message}`;

    }

}


// ============================================================
// VERIFY SELECTED
// ============================================================

async function verifySelected() {

    const evidenceId =
        prompt(
            "Enter Evidence ID to verify:"
        );


    if (!evidenceId) {
        return;
    }


    try {

        const response =
            await fetch(
                `${API_BASE}/api/verify/${encodeURIComponent(evidenceId)}`
            );


        const data =
            await response.json();


        if (!response.ok) {
            throw new Error(
                data.detail || "Verification failed"
            );
        }


        alert(
            `Evidence: ${data.evidence_id}\n` +
            `Status: ${data.status}\n\n` +
            `${data.message}`
        );


        await loadEvidence();

    }

    catch (error) {

        alert(
            `Verification error: ${error.message}`
        );

    }

}


// ============================================================
// CORRELATION
// ============================================================

async function runCorrelation() {

    try {

        const response =
            await fetch(
                `${API_BASE}/api/correlate`
            );


        const data =
            await response.json();


        if (!response.ok) {
            throw new Error(
                data.detail || "Correlation failed"
            );
        }


        alert(
            `Cross-Evidence Correlation Complete\n\n` +
            `Events: ${data.count}`
        );

    }

    catch (error) {

        alert(
            `Correlation error: ${error.message}`
        );

    }

}


// ============================================================
// GENERATE REPORT
// ============================================================

async function generateReport() {

    try {

        const response =
            await fetch(
                `${API_BASE}/api/report`
            );


        const data =
            await response.json();


        if (!response.ok) {
            throw new Error(
                data.detail || "Report generation failed"
            );
        }


        alert(
            `Forensic report generated successfully!\n\n` +
            `File: ${data.filename}\n\n` +
            `Evidence: ${data.evidence_count}\n` +
            `Custody Events: ${data.custody_event_count}\n` +
            `Audit Logs: ${data.audit_log_count}`
        );

    }

    catch (error) {

        alert(
            `Report error: ${error.message}`
        );

    }

}


// ============================================================
// CUSTODY EVENTS COUNT
// ============================================================

async function loadCustodyCount() {

    try {

        const response =
            await fetch(
                `${API_BASE}/api/artefacts`
            );


        const data =
            await response.json();


        let total =
            0;


        for (
            const evidence of data.artefacts
        ) {

            const custodyResponse =
                await fetch(
                    `${API_BASE}/api/custody/${evidence.evidence_id}`
                );


            const custodyData =
                await custodyResponse.json();


            total +=
                custodyData.count || 0;

        }


        document.getElementById(
            "custodyEvents"
        ).textContent = total;

    }

    catch (error) {

        console.error(
            "Custody count error:",
            error
        );

    }

}


// ============================================================
// UTILITY FUNCTIONS
// ============================================================

function formatDate(dateString) {

    if (!dateString) {
        return "-";
    }


    return new Date(
        dateString
    ).toLocaleString();

}


function escapeHtml(value) {

    const div =
        document.createElement(
            "div"
        );

    div.textContent =
        value;

    return div.innerHTML;

}


// ============================================================
// INITIALIZE
// ============================================================

window.addEventListener(
    "DOMContentLoaded",
    async () => {

        await loadDashboard();

        await loadCustodyCount();

    }
);