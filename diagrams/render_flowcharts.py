"""Render every current diagram from specs.py to Mermaid, SVG, PNG and PDF."""
from __future__ import annotations
import argparse
from html import escape
import os
from pathlib import Path
import tempfile

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "labtune-mpl"))
from specs import COLORS, DATE, STYLE, diagrams

OUT = Path(__file__).resolve().parent


def mermaid(g):
    lines = [f"%% Generated from specs.py; {g.get('date', DATE)}. Current runtime; gray nodes are planned.",
             "flowchart " + g["direction"]]
    for n in g["nodes"]:
        label = escape(n["title"] + ("\n" + n["body"] if n["body"] else ""), quote=True).replace("\n", "<br/>")
        lines.append(f'    {n["key"]}["{label}"]')
    for e in g["edges"]:
        arrow = "-.->" if e["optional"] else "-->"
        label = "|"+escape(e["label"]).replace("\n","<br/>")+"|" if e["label"] else ""
        lines.append(f'    {e["source"]} {arrow}{label} {e["target"]}')
    for kind, (fill, stroke) in COLORS.items():
        lines.append(f"    classDef {kind} fill:{fill},stroke:{stroke},color:{STYLE['ink']};")
        ids = ",".join(n["key"] for n in g["nodes"] if n["kind"] == kind)
        if ids:
            lines.append(f"    class {ids} {kind};")
    lines.append(f"    linkStyle default stroke:{STYLE['connector']},stroke-width:1.5px;")
    return "\n".join(lines) + "\n"


def render(g):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrowPatch, Polygon
    from matplotlib.path import Path as PlotPath
    plt.rcParams.update({"font.family": STYLE["body_font"], "svg.fonttype": "none"})
    width,height=g["width"],g["height"]
    fig,ax=plt.subplots(figsize=(width,height),facecolor=STYLE["background"])
    fig.subplots_adjust(left=0,right=1,bottom=0,top=1)
    ax.set(xlim=(0,width),ylim=(height,0));ax.axis("off")
    ax.text(.6,.45,g.get("brand", "LABTUNE")+" / "+g["stem"][:2],fontsize=11,color=STYLE["accent"],weight="bold",fontfamily=STYLE["display_font"],va="center")
    ax.text(width-.6,.45,g.get("date", DATE)+" · CURRENT BOUNDED RUNTIME",fontsize=10,color=STYLE["secondary"],ha="right",va="center")
    for y in (.7,.75):
        ax.plot([.6,width-.6],[y,y],color=STYLE["accent"],linewidth=.5)
    ax.text(.6,1.15,g["title"],fontsize=24,color=STYLE["ink"],weight="bold",fontfamily=STYLE["display_font"],va="center")
    ax.text(.6,1.75,g["subtitle"],fontsize=12,color=STYLE["secondary"],va="center")
    nodes={n["key"]:n for n in g["nodes"]}
    def port(key,side):
        n=nodes[key];x,y,w,h=n["x"],n["y"],n["w"],n["h"]
        return {"left":(x-w/2-.025,y),"right":(x+w/2+.025,y),
                "top":(x,y-h/2-.025),"bottom":(x,y+h/2+.025)}[side]
    for e in g["edges"]:
        pts=[port(e["source"],e["start"]),*e["via"],port(e["target"],e["end"])]
        color=COLORS["optional"][1] if e["optional"] else STYLE["connector"]
        ax.add_patch(FancyArrowPatch(path=PlotPath(pts,[PlotPath.MOVETO]+[PlotPath.LINETO]*(len(pts)-1)),
                     arrowstyle="-|>",mutation_scale=15,linewidth=1.6,color=color,
                     linestyle=(0,(4,3)) if e["optional"] else "solid",zorder=1))
        if e["label"]:
            xy=e["at"] or ((pts[0][0]+pts[-1][0])/2,(pts[0][1]+pts[-1][1])/2-.2)
            ax.text(*xy,e["label"],fontsize=9.5,color=color,ha="center",va="center",zorder=5,
                    bbox=dict(facecolor=STYLE["background"],edgecolor="none",pad=2))
    for n in g["nodes"]:
        fill,stroke=COLORS[n["kind"]]
        x,y,w,h=n["x"],n["y"],n["w"],n["h"]
        left,right,top,bottom=x-w/2,x+w/2,y-h/2,y+h/2
        cut=.09
        corners=[(left+cut,top),(right-cut,top),(right,top+cut),(right,bottom-cut),
                 (right-cut,bottom),(left+cut,bottom),(left,bottom-cut),(left,top+cut)]
        ax.add_patch(Polygon(corners,closed=True,
                     facecolor=fill,edgecolor=stroke,linewidth=1.5,zorder=3,
                     linestyle=(0,(5,3)) if n["kind"]=="future" else "solid"))
        for rule_y in (top+.08,bottom-.08):
            ax.plot([left+.16,right-.16],[rule_y,rule_y],color=stroke,alpha=.35,linewidth=.55,zorder=4)
        ax.text(x,y-h/2+.34,n["title"],fontsize=12,color=STYLE["ink"],weight="bold",fontfamily=STYLE["display_font"],
                ha="center",va="center",zorder=4)
        if n["body"]:
            ax.text(x,y+.22,n["body"],fontsize=10.2,color=STYLE["secondary"],ha="center",va="center",
                    linespacing=1.35,zorder=4)
    ax.plot([.6,width-.6],[height-.9,height-.9],color=STYLE["fine_rule"],linewidth=1)
    ax.text(.6,height-.47,g["footer"],fontsize=10.5,color=STYLE["secondary"],va="center")
    for suffix in ("svg","png","pdf"):
        target = OUT/(g["stem"]+"."+suffix)
        fig.savefig(target,dpi=130,facecolor=STYLE["background"],
                    metadata={"Creator":"Labtune diagram renderer"})
        if suffix == "svg":
            # Matplotlib pads multiline path attributes; keep generated text Git-clean.
            lines = target.read_text(encoding="utf-8").splitlines()
            target.write_text("\n".join(line.rstrip() for line in lines) + "\n",encoding="utf-8")
    plt.close(fig)


def overview(selected):
    from PIL import Image, ImageOps, ImageDraw
    sheet=Image.new("RGB",(1800,((len(selected)+2)//3)*420),STYLE["background"])
    for i,g in enumerate(selected):
        with Image.open(OUT/(g["stem"]+".png")) as source:
            tile=ImageOps.contain(source.convert("RGB"),(590,405))
            sheet.paste(tile,((i%3)*600+(600-tile.width)//2,(i//3)*420))
    sheet.save(OUT/"overview.png")


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--mermaid-only",action="store_true")
    parser.add_argument("--diagram",action="append",help="Regenerate only a named diagram stem; may be repeated")
    args=parser.parse_args()
    all_specs=diagrams()
    if args.diagram and set(args.diagram)-{g["stem"] for g in all_specs}:
        parser.error("Unknown diagram stem")
    selected=[g for g in all_specs if not args.diagram or g["stem"] in args.diagram]
    for g in selected:
        (OUT/(g["stem"]+".mmd")).write_text(mermaid(g),encoding="utf-8")
        if not args.mermaid_only:
            render(g)
    if not args.mermaid_only:
        overview(all_specs)
    print(f"Updated {len(selected)} diagrams from one specification.")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
