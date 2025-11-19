# Cover Image Instructions for Azure HayMaker Presentation

## Image Requirements

**Subject**: Hay bales on a farm (haystack/hay field)
**Dimensions**: 1920x1080 (16:9 aspect ratio)
**Style**: Professional but approachable
**Color Palette**: Warm tones (golden, amber, earth tones)
**Usage**: Cover slide background with title overlay

---

## Option 1: Creative Commons Images (Recommended)

### Unsplash (Free, No Attribution Required)

**Search Terms**:
- "hay bales"
- "haystack"
- "hay field"
- "straw bales"
- "farm field"

**Recommended URLs** (check availability):
1. https://unsplash.com/s/photos/hay-bales
2. https://unsplash.com/s/photos/haystack
3. https://unsplash.com/s/photos/farm-field

**Download Steps**:
```bash
# Using command line
curl -L "https://unsplash.com/photos/{photo-id}/download?force=true" \
  -o presentation-assets/haystack-cover.jpg

# Or download manually from website
# Click "Download" button → Select "Large (1920x1280)" or higher
# Save to: presentation-assets/haystack-cover.jpg
```

**Recommended Image Characteristics**:
- Sunlit hay bales (warm golden hour lighting)
- Clear blue sky or sunset background
- Not too busy (leave space for title overlay)
- Horizontal composition
- Shallow depth of field (blurred background optional)

---

### Pexels (Free, No Attribution Required)

**Search Terms**: Same as Unsplash

**Recommended URLs**:
1. https://www.pexels.com/search/hay%20bales/
2. https://www.pexels.com/search/haystack/

**Download Steps**:
```bash
# Download manually from website
# Select "Large (1920x1279)" or "Original"
# Save to: presentation-assets/haystack-cover.jpg
```

---

### Pixabay (Free, No Attribution Required)

**Search Terms**: Same as above

**URL**: https://pixabay.com/images/search/hay%20bales/

**Download**: Same process as Pexels

---

## Option 2: Generate with AI (If Available)

### DALL-E 3 / Midjourney / Stable Diffusion

**Prompt**:
```
A professional photograph of golden hay bales in a sunlit farm field.
Warm afternoon lighting with clear blue sky. Rustic and natural,
pastoral scene. Shot with shallow depth of field. High quality,
cinematic composition. Photorealistic. 16:9 aspect ratio.
```

**Alternative Prompt (More Abstract)**:
```
Aerial view of organized hay bales in a harvested field forming a
pattern. Golden hour lighting. Warm earth tones. Professional
agricultural photography. Clean composition with copy space at top.
16:9 aspect ratio.
```

**Settings**:
- Aspect Ratio: 16:9 (1920x1080)
- Style: Photographic
- Quality: High
- Detail: High

**Save As**: `presentation-assets/haystack-cover-generated.png`

---

## Option 3: Use Placeholder with Microsoft Stock

### Microsoft 365 Stock Images

If creating in PowerPoint:
1. Open PowerPoint
2. Insert → Stock Images
3. Search: "hay bales" or "farm"
4. Select appropriate image
5. Apply as slide background
6. Export slide as image (1920x1080)

---

## Option 4: Manual Photography (If Available)

If you have access to a farm or rural area:

**Camera Settings**:
- Aperture: f/2.8 - f/5.6 (shallow depth of field)
- ISO: 100-400 (low for quality)
- Shutter: 1/250s or faster
- White Balance: Daylight or Auto
- Format: RAW or highest quality JPEG

**Composition**:
- Rule of thirds (hay bales in lower third)
- Leave space in upper third for title overlay
- Shoot during golden hour (1 hour before sunset)
- Avoid harsh midday sun

**Post-Processing**:
- Adjust exposure if needed
- Enhance warm tones slightly
- Crop to 16:9 (1920x1080)
- Export as JPEG (high quality)

---

## Selected Image Preparation

Once you have the source image:

### Step 1: Resize (if needed)
```bash
# Using ImageMagick
convert source-image.jpg -resize 1920x1080^ -gravity center -extent 1920x1080 haystack-cover.jpg

# Using Python (PIL)
python3 << 'EOF'
from PIL import Image

img = Image.open("source-image.jpg")
img = img.resize((1920, 1080), Image.Resampling.LANCZOS)
img.save("haystack-cover.jpg", quality=95)
EOF
```

### Step 2: Optimize for Web
```bash
# Reduce file size without losing quality
convert haystack-cover.jpg -quality 85 -strip haystack-cover-optimized.jpg
```

### Step 3: Add Subtle Overlay (Optional)
```bash
# Darken image slightly for better text readability
convert haystack-cover.jpg -brightness-contrast -5x0 haystack-cover-darkened.jpg

# Add gradient overlay (dark at top for title)
convert haystack-cover.jpg \
  \( -size 1920x1080 gradient:transparent-'rgba(0,0,0,0.4)' \) \
  -compose multiply -composite \
  haystack-cover-overlay.jpg
```

---

## PowerPoint Integration

### Adding to Cover Slide

**Method 1: Background Image**
```
1. Select slide 1 (cover slide)
2. Right-click → Format Background
3. Fill → Picture or texture fill
4. File → Select haystack-cover.jpg
5. Transparency: 0% (or 10-20% if too bright)
6. Offset: Centered
```

**Method 2: Insert as Picture**
```
1. Insert → Pictures → This Device
2. Select haystack-cover.jpg
3. Right-click → Send to Back
4. Resize to fill slide (1920x1080)
5. Position: 0,0 (top-left corner)
```

### Text Overlay for Title

**Recommended Settings**:
- Title text: White or light color
- Font: Segoe UI Bold or similar
- Size: 60-72pt
- Position: Upper third or center
- Shadow: Optional (subtle drop shadow for readability)
- Background: Optional semi-transparent rectangle behind text

**Example Layout**:
```
┌─────────────────────────────────────────┐
│                                         │
│         AZURE HAYMAKER                  │  ← White, 72pt, Bold
│  Autonomous Cloud Security Testing     │  ← White, 36pt, Regular
│    with AI Agents                       │
│                                         │
│    [Hay bales image fills background]  │
│                                         │
│                           November 2025 │  ← White, 24pt, Bottom right
└─────────────────────────────────────────┘
```

---

## Fallback Options

### If No Suitable Image Found

**Option A: Use Solid Color with Logo**
- Background: Azure blue (#0078D4)
- Title: White text
- Subtitle: Light blue text
- Add Azure logo or HayMaker icon

**Option B: Abstract Pattern**
- Use geometric pattern suggesting organization/structure
- Colors: Earth tones (browns, golds, greens)
- Minimalist design

**Option C: Text-Only Cover**
- Professional typography
- Gradient background (earth tones)
- Clean, modern design

---

## Quick Setup Script

```bash
#!/bin/bash
# Quick setup for cover image from Unsplash

cd presentation-assets

# Download from Unsplash (example - replace with actual photo ID)
PHOTO_ID="your-chosen-photo-id"
curl -L "https://unsplash.com/photos/${PHOTO_ID}/download?force=true" \
  -o haystack-cover-source.jpg

# Resize to exact dimensions
convert haystack-cover-source.jpg \
  -resize 1920x1080^ \
  -gravity center \
  -extent 1920x1080 \
  -quality 90 \
  haystack-cover.jpg

# Create version with subtle darkening for text overlay
convert haystack-cover.jpg \
  -brightness-contrast -10x0 \
  haystack-cover-darkened.jpg

echo "Cover images created:"
echo "  - haystack-cover.jpg (original, 1920x1080)"
echo "  - haystack-cover-darkened.jpg (darkened for text overlay)"
```

---

## Recommended Image Examples

### Style 1: Classic Farm Scene
- Multiple hay bales in a field
- Golden hour lighting
- Clear sky
- Pastoral, peaceful feeling

### Style 2: Close-up Detail
- Single hay bale or small group
- Textured detail visible
- Blurred background
- More abstract

### Style 3: Aerial/Pattern
- Organized rows of hay bales
- Bird's eye view
- Geometric pattern
- Modern, clean aesthetic

### Style 4: Sunset Silhouette
- Hay bales silhouetted against sunset
- Dramatic lighting
- Warm color palette
- Inspirational mood

---

## Legal Considerations

### Ensure License Allows
- Commercial use (if presenting to clients)
- Modification (if adding overlays)
- No attribution required (preferred for professional presentations)

### Recommended Licenses
- Unsplash License (free to use, no attribution)
- Pexels License (free to use, no attribution)
- Pixabay License (free to use, no attribution)
- Creative Commons CC0 (public domain)

### Avoid
- Getty Images without license
- Stock photos requiring attribution in slides
- Copyrighted images without permission

---

## Final Checklist

Before using in presentation:
- [ ] Image is 1920x1080 (16:9 ratio)
- [ ] Image quality is high (no pixelation)
- [ ] Colors are warm and professional
- [ ] Composition allows for title overlay
- [ ] License allows commercial use
- [ ] File size is reasonable (<5MB)
- [ ] Image saved to: `presentation-assets/haystack-cover.jpg`

---

## Example Commands to Execute

```bash
# Create assets directory if needed
mkdir -p presentation-assets

# Download recommended image from Unsplash (manual step - browser)
# Visit: https://unsplash.com/s/photos/hay-bales
# Download high-res image

# Or use curl if you have direct URL
cd presentation-assets
curl -L "https://images.unsplash.com/photo-XXXXXXXXX?w=1920&h=1080&fit=crop" \
  -o haystack-cover.jpg

# Verify dimensions
file haystack-cover.jpg

# Open in preview to check quality
open haystack-cover.jpg  # macOS
xdg-open haystack-cover.jpg  # Linux
```

---

**STATUS**: Ready for image sourcing. Follow Option 1 (Unsplash) for fastest, highest-quality result.

**RECOMMENDATION**: Search Unsplash for "hay bales sunset" to get warm, professional images perfect for title overlay.
