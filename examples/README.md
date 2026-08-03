# Examples

Developer and demo scripts. These are **not** part of the installed
`deskos` package - they live here so the shipped application surface stays
limited to real product code.

Run them from the repository root:

```bash
python examples/demo_widget.py     # show the floating widget directly
python examples/demo_pipeline.py   # type a context state, watch it flow through the real layers
```

`demo_pipeline.py` is the more useful of the two: it exercises the actual
Reasoning -> Decision -> Services path, including DeskOS deciding to stay
silent, which is the behaviour hardest to observe in normal use.
