from collections import Counter


class Assembler:
    """Joins chunk transcripts into a single output string."""

    def assemble(self, chunk_results):
        """
        Parameters
        ----------
        chunk_results : list of (start_sec, end_sec, transcript, info_dict)

        Returns
        -------
        (full_transcript, route_summary_str)
        """
        parts = [text.strip() for _, _, text, _ in chunk_results if text.strip()]
        routes = [info["route"] for _, _, _, info in chunk_results]
        return " ".join(parts), _summarise(routes)


def _summarise(routes):
    c = Counter(routes)
    parts = []
    if c.get("whisper"):
        parts.append(f"English×{c['whisper']}")
    if c.get("indic"):
        parts.append(f"Indian×{c['indic']}")
    if c.get("mixed"):
        parts.append(f"Mixed×{c['mixed']}")
    if c.get("whisper-fallback"):
        parts.append(f"Fallback×{c['whisper-fallback']}")
    return " | ".join(parts) if parts else "silence"
