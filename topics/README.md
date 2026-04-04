# Chapter-wise Python notes

Put Markdown (or other source) per chapter here, for example:

- `chapter_01_intro.md`
- `chapter_02_functions.md`

These files are exposed read-only over HTTP at **`/study/topics/`** (see `ApiConstants.STUDY_TOPICS_MOUNT_PATH`).

Convert to PDF into `media/` with:

```bash
uv run python tools/md_to_pdf.py topics/your_chapter.md -o media/
```
