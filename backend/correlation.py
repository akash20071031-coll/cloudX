from datetime import datetime


def correlate_evidence(evidence_list):
    """
    Create a simple chronological correlation
    between available evidence artefacts.
    """

    timeline = []

    for evidence in evidence_list:

        timeline.append({
            "evidence_id": evidence.evidence_id,
            "filename": evidence.filename,
            "event": "Evidence uploaded",
            "timestamp": evidence.uploaded_at,
            "status": evidence.status
        })

    # Sort events chronologically
    timeline.sort(
        key=lambda x: x["timestamp"] or datetime.min
    )

    return timeline