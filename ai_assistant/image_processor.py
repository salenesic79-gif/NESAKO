import os
import base64
import json
from PIL import Image, ImageEnhance, ImageFilter
import io
import tempfile
from typing import Dict, List, Tuple, Optional
import requests

class ImageProcessor:
    """Napredni sistem za obradu slika sa AI analizom"""
    
    def __init__(self):
        self.supported_formats = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.max_dimensions = (2048, 2048)
        
    def process_uploaded_image(self, image_data: bytes, filename: str) -> Dict:
        """Obrađuje upload-ovanu sliku"""
        try:
            # Validate file
            validation_result = self.validate_image(image_data, filename)
            if not validation_result['valid']:
                return validation_result
            
            # Open image
            image = Image.open(io.BytesIO(image_data))
            
            # Get basic info
            image_info = self.get_image_info(image, filename)
            
            # Resize if needed
            if image.size[0] > self.max_dimensions[0] or image.size[1] > self.max_dimensions[1]:
                image = self.resize_image(image, self.max_dimensions)
                image_info['resized'] = True
            
            # Convert to base64 for storage/display
            buffered = io.BytesIO()
            image.save(buffered, format=image.format or 'JPEG')
            image_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            # Analyze image content
            analysis = self.analyze_image_content(image)
            
            return {
                'success': True,
                'image_info': image_info,
                'image_base64': image_base64,
                'analysis': analysis,
                'processing_steps': ['validation', 'info_extraction', 'resize', 'analysis']
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Greška pri obradi slike: {str(e)}',
                'error_type': 'processing_error'
            }
    
    def validate_image(self, image_data: bytes, filename: str) -> Dict:
        """Validira upload-ovanu sliku"""
        try:
            # Check file size
            if len(image_data) > self.max_file_size:
                return {
                    'valid': False,
                    'error': f'Slika je prevelika. Maksimalna veličina: {self.max_file_size // (1024*1024)}MB',
                    'error_type': 'file_too_large'
                }
            
            # Check file extension
            file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
            if file_ext not in self.supported_formats:
                return {
                    'valid': False,
                    'error': f'Nepodržan format. Podržani formati: {", ".join(self.supported_formats)}',
                    'error_type': 'unsupported_format'
                }
            
            # Try to open image
            try:
                image = Image.open(io.BytesIO(image_data))
                image.verify()  # Verify it's a valid image
            except Exception:
                return {
                    'valid': False,
                    'error': 'Fajl nije validna slika',
                    'error_type': 'invalid_image'
                }
            
            return {'valid': True}
            
        except Exception as e:
            return {
                'valid': False,
                'error': f'Greška pri validaciji: {str(e)}',
                'error_type': 'validation_error'
            }
    
    def get_image_info(self, image: Image.Image, filename: str) -> Dict:
        """Izvlači informacije o slici"""
        try:
            info = {
                'filename': filename,
                'format': image.format,
                'mode': image.mode,
                'size': image.size,
                'width': image.size[0],
                'height': image.size[1],
                'has_transparency': image.mode in ('RGBA', 'LA') or 'transparency' in image.info,
                'color_mode': self.get_color_mode_description(image.mode),
                'estimated_colors': len(image.getcolors(maxcolors=256)) if image.getcolors(maxcolors=256) else 'više od 256'
            }
            
            # Add EXIF data if available
            if hasattr(image, '_getexif') and image._getexif():
                exif = image._getexif()
                if exif:
                    info['has_exif'] = True
                    # Extract common EXIF tags
                    exif_tags = {
                        'DateTime': 306,
                        'Make': 271,
                        'Model': 272,
                        'Software': 305
                    }
                    for tag_name, tag_id in exif_tags.items():
                        if tag_id in exif:
                            info[f'exif_{tag_name.lower()}'] = exif[tag_id]
            
            return info
            
        except Exception as e:
            return {
                'filename': filename,
                'error': f'Greška pri čitanju informacija: {str(e)}'
            }
    
    def get_color_mode_description(self, mode: str) -> str:
        """Vraća opis color mode-a"""
        descriptions = {
            'RGB': 'RGB (crvena, zelena, plava)',
            'RGBA': 'RGBA (RGB + alpha kanal)',
            'L': 'Grayscale (crno-bela)',
            'P': 'Palette (indeksovane boje)',
            'CMYK': 'CMYK (cyan, magenta, žuta, crna)',
            '1': 'Bitmap (1-bit crno-bela)'
        }
        return descriptions.get(mode, f'Nepoznat ({mode})')
    
    def resize_image(self, image: Image.Image, max_size: Tuple[int, int]) -> Image.Image:
        """Resize sliku zadržavajući aspect ratio"""
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        return image
    
    def analyze_image_content(self, image: Image.Image) -> Dict:
        """Analizira sadržaj slike"""
        try:
            analysis = {
                'brightness': self.calculate_brightness(image),
                'contrast': self.calculate_contrast(image),
                'dominant_colors': self.get_dominant_colors(image),
                'image_type': self.classify_image_type(image),
                'quality_assessment': self.assess_image_quality(image)
            }
            
            return analysis
            
        except Exception as e:
            return {
                'error': f'Greška pri analizi: {str(e)}'
            }
    
    def calculate_brightness(self, image: Image.Image) -> float:
        """Računa prosečnu svetlost slike"""
        try:
            # Convert to grayscale if needed
            if image.mode != 'L':
                gray_image = image.convert('L')
            else:
                gray_image = image
            
            # Calculate average brightness
            pixels = list(gray_image.getdata())
            brightness = sum(pixels) / len(pixels)
            return round(brightness / 255.0, 2)  # Normalize to 0-1
            
        except Exception:
            return 0.5
    
    def calculate_contrast(self, image: Image.Image) -> float:
        """Računa kontrast slike"""
        try:
            # Convert to grayscale
            if image.mode != 'L':
                gray_image = image.convert('L')
            else:
                gray_image = image
            
            # Calculate standard deviation as contrast measure
            pixels = list(gray_image.getdata())
            mean = sum(pixels) / len(pixels)
            variance = sum((p - mean) ** 2 for p in pixels) / len(pixels)
            contrast = (variance ** 0.5) / 255.0  # Normalize
            
            return round(contrast, 2)
            
        except Exception:
            return 0.5
    
    def get_dominant_colors(self, image: Image.Image, num_colors: int = 5) -> List[Dict]:
        """Pronalazi dominantne boje u slici"""
        try:
            # Convert to RGB if needed
            if image.mode != 'RGB':
                rgb_image = image.convert('RGB')
            else:
                rgb_image = image
            
            # Get colors
            colors = rgb_image.getcolors(maxcolors=256*256*256)
            if not colors:
                return []
            
            # Sort by frequency and take top colors
            colors.sort(key=lambda x: x[0], reverse=True)
            dominant_colors = []
            
            for i, (count, color) in enumerate(colors[:num_colors]):
                percentage = (count / (image.size[0] * image.size[1])) * 100
                dominant_colors.append({
                    'rank': i + 1,
                    'rgb': color,
                    'hex': f'#{color[0]:02x}{color[1]:02x}{color[2]:02x}',
                    'percentage': round(percentage, 1)
                })
            
            return dominant_colors
            
        except Exception:
            return []
    
    def classify_image_type(self, image: Image.Image) -> str:
        """Klasifikuje tip slike na osnovu karakteristika"""
        try:
            width, height = image.size
            aspect_ratio = width / height
            
            # Basic classification based on dimensions and aspect ratio
            if width > 1920 or height > 1080:
                size_category = 'high_resolution'
            elif width < 300 or height < 300:
                size_category = 'thumbnail'
            else:
                size_category = 'standard'
            
            if 0.9 <= aspect_ratio <= 1.1:
                shape = 'square'
            elif aspect_ratio > 1.5:
                shape = 'landscape'
            elif aspect_ratio < 0.67:
                shape = 'portrait'
            else:
                shape = 'standard'
            
            # Check if it's likely a screenshot
            if (width % 16 == 0 and height % 9 == 0) or aspect_ratio in [16/9, 4/3, 16/10]:
                content_type = 'possible_screenshot'
            else:
                content_type = 'photo_or_graphic'
            
            return f'{size_category}_{shape}_{content_type}'
            
        except Exception:
            return 'unknown'
    
    def assess_image_quality(self, image: Image.Image) -> Dict:
        """Procenjuje kvalitet slike"""
        try:
            width, height = image.size
            total_pixels = width * height
            
            # Resolution assessment
            if total_pixels > 2000000:  # > 2MP
                resolution_quality = 'high'
            elif total_pixels > 500000:  # > 0.5MP
                resolution_quality = 'medium'
            else:
                resolution_quality = 'low'
            
            # Brightness assessment
            brightness = self.calculate_brightness(image)
            if 0.2 <= brightness <= 0.8:
                brightness_quality = 'good'
            elif 0.1 <= brightness <= 0.9:
                brightness_quality = 'acceptable'
            else:
                brightness_quality = 'poor'
            
            # Contrast assessment
            contrast = self.calculate_contrast(image)
            if contrast > 0.3:
                contrast_quality = 'good'
            elif contrast > 0.15:
                contrast_quality = 'acceptable'
            else:
                contrast_quality = 'poor'
            
            # Overall quality
            quality_scores = {
                'high': 3, 'good': 3,
                'medium': 2, 'acceptable': 2,
                'low': 1, 'poor': 1
            }
            
            total_score = (
                quality_scores.get(resolution_quality, 1) +
                quality_scores.get(brightness_quality, 1) +
                quality_scores.get(contrast_quality, 1)
            )
            
            if total_score >= 8:
                overall = 'excellent'
            elif total_score >= 6:
                overall = 'good'
            elif total_score >= 4:
                overall = 'acceptable'
            else:
                overall = 'poor'
            
            return {
                'resolution': resolution_quality,
                'brightness': brightness_quality,
                'contrast': contrast_quality,
                'overall': overall,
                'score': f'{total_score}/9'
            }
            
        except Exception:
            return {
                'overall': 'unknown',
                'error': 'Greška pri proceni kvaliteta'
            }
    
    def enhance_image(self, image: Image.Image, enhancement_type: str = 'auto') -> Image.Image:
        """Poboljšava sliku"""
        try:
            if enhancement_type == 'auto':
                # Auto enhancement based on image analysis
                brightness = self.calculate_brightness(image)
                contrast = self.calculate_contrast(image)
                
                enhanced = image.copy()
                
                # Adjust brightness if needed
                if brightness < 0.3:
                    enhancer = ImageEnhance.Brightness(enhanced)
                    enhanced = enhancer.enhance(1.2)
                elif brightness > 0.8:
                    enhancer = ImageEnhance.Brightness(enhanced)
                    enhanced = enhancer.enhance(0.9)
                
                # Adjust contrast if needed
                if contrast < 0.2:
                    enhancer = ImageEnhance.Contrast(enhanced)
                    enhanced = enhancer.enhance(1.3)
                
                return enhanced
            
            elif enhancement_type == 'sharpen':
                return image.filter(ImageFilter.SHARPEN)
            
            elif enhancement_type == 'blur':
                return image.filter(ImageFilter.BLUR)
            
            else:
                return image
                
        except Exception:
            return image
    
    def generate_image_description(self, analysis: Dict, image_info: Dict) -> str:
        """Generiše opis slike na srpskom"""
        try:
            description_parts = []
            
            # Basic info
            width = image_info.get('width', 0)
            height = image_info.get('height', 0)
            format_name = image_info.get('format', 'nepoznat')
            
            description_parts.append(f"Slika dimenzija {width}x{height} piksela u {format_name} formatu")
            
            # Quality assessment
            quality = analysis.get('quality_assessment', {})
            overall_quality = quality.get('overall', 'nepoznat')
            description_parts.append(f"Kvalitet: {overall_quality}")
            
            # Brightness and contrast
            brightness = analysis.get('brightness', 0)
            contrast = analysis.get('contrast', 0)
            
            if brightness < 0.3:
                description_parts.append("Slika je prilično tamna")
            elif brightness > 0.7:
                description_parts.append("Slika je prilično svetla")
            else:
                description_parts.append("Slika ima dobru osvetljenost")
            
            if contrast < 0.2:
                description_parts.append("nizak kontrast")
            elif contrast > 0.4:
                description_parts.append("visok kontrast")
            else:
                description_parts.append("umeren kontrast")
            
            # Dominant colors
            dominant_colors = analysis.get('dominant_colors', [])
            if dominant_colors:
                top_color = dominant_colors[0]
                description_parts.append(f"Dominantna boja: {top_color['hex']} ({top_color['percentage']}%)")
            
            # Image type
            image_type = analysis.get('image_type', '')
            if 'screenshot' in image_type:
                description_parts.append("Verovatno screenshot")
            elif 'landscape' in image_type:
                description_parts.append("Landscape orijentacija")
            elif 'portrait' in image_type:
                description_parts.append("Portrait orijentacija")
            
            return ". ".join(description_parts) + "."
            
        except Exception:
            return "Analiza slike završena."
