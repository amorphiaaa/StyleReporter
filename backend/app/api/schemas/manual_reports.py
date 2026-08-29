from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReportTextBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intro: str = ""
    items: list[str] = Field(default_factory=list)


class PaletteColor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = ""
    hex: str = ""
    description: str = ""
    works_with: str = ""


class PaletteSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intro: str = ""
    colors: list[PaletteColor] = Field(default_factory=list)


class GuidanceSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intro: str = ""
    what_works: list[str] = Field(default_factory=list)
    how_to_use: list[str] = Field(default_factory=list)


class SilhouetteItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = ""
    description: str = ""


class SilhouetteSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intro: str = ""
    outer_layers: list[SilhouetteItem] = Field(default_factory=list)
    bottoms: list[SilhouetteItem] = Field(default_factory=list)
    tops_and_knitwear: list[SilhouetteItem] = Field(default_factory=list)
    dresses: list[SilhouetteItem] = Field(default_factory=list)


class NamedListSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = ""
    items: list[str] = Field(default_factory=list)


class AccessoriesSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intro: str = ""
    core_elements: list[str] = Field(default_factory=list)
    use_principles: list[str] = Field(default_factory=list)
    categories: list[NamedListSection] = Field(default_factory=list)


class OutfitFormula(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = ""
    occasions: list[str] = Field(default_factory=list)
    logic: str = ""
    steps: list[str] = Field(default_factory=list)


class StyleAnchor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = ""
    description: str = ""


class DistractionSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intro: str = ""
    colors: list[str] = Field(default_factory=list)
    prints: list[str] = Field(default_factory=list)
    silhouettes: list[str] = Field(default_factory=list)


class BrandCategory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str = ""
    brands: list[str] = Field(default_factory=list)


class MoodboardItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = ""
    url: str = ""
    note: str = ""


class ActionPlanItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = ""
    body: str = ""


class ManualReportImageGroup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    group_key: str = ""
    label: str = ""
    instructions: str = ""
    asset_keys: list[str] = Field(default_factory=list)


class ManualStyleReportContent(BaseModel):
    """Editable content blocks that mirror the supplied portfolio template."""

    model_config = ConfigDict(extra="forbid")

    source_text: str = ""
    image_groups: list[ManualReportImageGroup] = Field(default_factory=list)
    how_to_use: ReportTextBlock = Field(default_factory=ReportTextBlock)
    title: str = ""
    alignment_summary: str = ""
    current_style_language: list[str] = Field(default_factory=list)
    desired_style_language: list[str] = Field(default_factory=list)
    disconnect: str = ""
    style_language_summary: str = ""
    style_language_anchors: list[str] = Field(default_factory=list)
    color_palette: dict[str, PaletteSection] = Field(default_factory=dict)
    prints_and_textures: GuidanceSection = Field(default_factory=GuidanceSection)
    silhouettes: SilhouetteSection = Field(default_factory=SilhouetteSection)
    accessories: AccessoriesSection = Field(default_factory=AccessoriesSection)
    outfit_formulas: list[OutfitFormula] = Field(default_factory=list)
    style_anchors: list[StyleAnchor] = Field(default_factory=list)
    what_can_distract: DistractionSection = Field(default_factory=DistractionSection)
    brands: list[BrandCategory] = Field(default_factory=list)
    moodboard: list[MoodboardItem] = Field(default_factory=list)
    action_plan: list[ActionPlanItem] = Field(default_factory=list)


class ManualStyleReportResponse(BaseModel):
    id: UUID
    client_id: UUID
    submission_id: UUID
    content: dict[str, Any]
    created_at: datetime | None
    updated_at: datetime | None
