/**
 * Image Processing Utilities
 * Uses Sharp for image manipulation and SVG overlay
 */

import sharp from 'sharp';
import { Rect, Point, CoordinateGridOptions, ImageProcessingOptions } from '../types/index.js';

/**
 * Add a coordinate grid overlay to an image using SVG
 */
export async function addCoordinateGrid(
  imageBuffer: Buffer,
  options?: CoordinateGridOptions
): Promise<Buffer> {
  const spacing = options?.spacing || 100;
  const gridColor = options?.gridColor || 'rgba(128, 128, 128, 0.3)';
  const gridWidth = options?.gridWidth || 1;

  const image = sharp(imageBuffer);
  const metadata = await image.metadata();

  if (!metadata.width || !metadata.height) {
    return imageBuffer;
  }

  const width = metadata.width;
  const height = metadata.height;

  // Generate SVG grid lines
  let svgLines = '';

  // Vertical lines
  for (let x = spacing; x < width; x += spacing) {
    svgLines += `<line x1="${x}" y1="0" x2="${x}" y2="${height}" stroke="${gridColor}" stroke-width="${gridWidth}" stroke-dasharray="5,5"/>`;
  }

  // Horizontal lines
  for (let y = spacing; y < height; y += spacing) {
    svgLines += `<line x1="0" y1="${y}" x2="${width}" y2="${y}" stroke="${gridColor}" stroke-width="${gridWidth}" stroke-dasharray="5,5"/>`;
  }

  const svg = `<svg width="${width}" height="${height}" xmlns="http://www.w3.org/2000/svg">${svgLines}</svg>`;

  return sharp(imageBuffer)
    .composite([
      {
        input: Buffer.from(svg),
        top: 0,
        left: 0,
      },
    ])
    .png()
    .toBuffer();
}

/**
 * Optimize image for AI consumption
 */
export async function optimizeForAI(
  imageBuffer: Buffer,
  options?: ImageProcessingOptions
): Promise<Buffer> {
  const maxWidth = options?.maxWidth || 1280;
  const quality = options?.quality || 80;

  let result = sharp(imageBuffer);
  const metadata = await result.metadata();

  if (metadata.width && metadata.width > maxWidth) {
    result = result.resize(maxWidth, undefined, {
      withoutEnlargement: true,
    });
  }

  return result.jpeg({ quality }).toBuffer();
}

/**
 * Crop a region from an image
 */
export async function cropRegion(imageBuffer: Buffer, region: Rect): Promise<Buffer> {
  return sharp(imageBuffer)
    .extract({
      left: Math.round(region.x),
      top: Math.round(region.y),
      width: Math.round(region.width),
      height: Math.round(region.height),
    })
    .png()
    .toBuffer();
}

/**
 * Annotate image with point markers and labels
 */
export async function annotatePoints(
  imageBuffer: Buffer,
  points: Array<{
    x: number;
    y: number;
    label?: string;
    color?: string;
  }>
): Promise<Buffer> {
  const image = sharp(imageBuffer);
  const metadata = await image.metadata();

  if (!metadata.width || !metadata.height) {
    return imageBuffer;
  }

  const width = metadata.width;
  const height = metadata.height;
  const radius = 8;
  const strokeWidth = 2;

  // Generate SVG annotations
  let svgElements = '';

  for (const point of points) {
    const color = point.color || '#FF0000';
    const x = Math.round(point.x);
    const y = Math.round(point.y);

    // Circle
    svgElements += `<circle cx="${x}" cy="${y}" r="${radius}" fill="none" stroke="${color}" stroke-width="${strokeWidth}"/>`;

    // Label if provided
    if (point.label) {
      const labelX = x + radius + 5;
      const labelY = y - 2;
      svgElements += `<text x="${labelX}" y="${labelY}" font-family="Arial, sans-serif" font-size="12" fill="${color}" font-weight="bold">${escapeXml(point.label)}</text>`;
    }
  }

  const svg = `<svg width="${width}" height="${height}" xmlns="http://www.w3.org/2000/svg">${svgElements}</svg>`;

  return sharp(imageBuffer)
    .composite([
      {
        input: Buffer.from(svg),
        top: 0,
        left: 0,
      },
    ])
    .png()
    .toBuffer();
}

/**
 * Escape XML special characters
 */
function escapeXml(str: string): string {
  const map: Record<string, string> = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&apos;',
  };

  return str.replace(/[&<>"']/g, (c) => map[c] || c);
}

/**
 * Convert image to grayscale
 */
export async function toGrayscale(imageBuffer: Buffer): Promise<Buffer> {
  return sharp(imageBuffer).grayscale().png().toBuffer();
}

/**
 * Apply blur to image
 */
export async function applyBlur(imageBuffer: Buffer, radius: number = 5): Promise<Buffer> {
  return sharp(imageBuffer).blur(radius).png().toBuffer();
}

/**
 * Resize image maintaining aspect ratio
 */
export async function resizeImage(
  imageBuffer: Buffer,
  maxWidth: number,
  maxHeight?: number
): Promise<Buffer> {
  return sharp(imageBuffer)
    .resize(maxWidth, maxHeight, {
      withoutEnlargement: true,
      fit: 'inside',
    })
    .png()
    .toBuffer();
}
