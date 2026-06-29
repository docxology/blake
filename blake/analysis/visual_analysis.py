"""
Visual analysis functionality for Blake images and illustrations.
"""

import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import logging
import numpy as np
from PIL import Image, ImageStat
import cv2

try:
    from sklearn.cluster import KMeans
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from ..models import BlakeImage, BlakeWork
from ..exceptions import AnalysisError

logger = logging.getLogger(__name__)


class VisualAnalyzer:
    """Visual analysis functionality for Blake images."""
    
    def __init__(self):
        """Initialize visual analyzer."""
        pass
    
    async def analyze_image(self, image: BlakeImage) -> Dict[str, Any]:
        """
        Perform comprehensive visual analysis on an image.
        
        Args:
            image: BlakeImage to analyze
            
        Returns:
            Dictionary of analysis results
        """
        if not image.file_path or not image.file_path.exists():
            return {'error': 'Image file not found'}
        
        logger.info(f"Analyzing image: {image.id}")
        
        try:
            results = {}
            
            # Load image
            pil_image = Image.open(image.file_path)
            img_array = np.array(pil_image)
            
            # Basic properties
            results['basic_properties'] = await self._analyze_basic_properties(image, pil_image, img_array)
            
            # Color analysis
            results['color_analysis'] = await self._analyze_colors(pil_image, img_array)
            
            # Composition analysis
            results['composition'] = await self._analyze_composition(img_array)
            
            # Edge and texture analysis
            results['texture'] = await self._analyze_texture(img_array)
            
            # Shape analysis
            results['shapes'] = await self._analyze_shapes(img_array)
            
            # Style analysis
            results['style'] = await self._analyze_style(img_array)
            
            logger.info(f"Completed visual analysis for image: {image.id}")
            return results
            
        except Exception as e:
            logger.error(f"Error analyzing image {image.id}: {e}")
            raise AnalysisError(f"Failed to analyze image: {e}")
    
    async def _analyze_basic_properties(self, image: BlakeImage, pil_image: Image.Image,
                                      img_array: np.ndarray) -> Dict[str, Any]:
        """Analyze basic image properties."""
        width, height = pil_image.size
        mode = pil_image.mode
        
        # Calculate aspect ratio
        aspect_ratio = width / height
        
        # Calculate area
        area = width * height
        
        # Calculate file size (if available)
        file_size = image.file_path.stat().st_size if image.file_path.exists() else None
        
        return {
            'width': width,
            'height': height,
            'mode': mode,
            'aspect_ratio': aspect_ratio,
            'area': area,
            'file_size': file_size,
        }
    
    async def _analyze_colors(self, pil_image: Image.Image, 
                            img_array: np.ndarray) -> Dict[str, Any]:
        """Analyze color properties of the image."""
        # Convert to RGB if necessary
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')
            img_array = np.array(pil_image)
        
        # Calculate color statistics
        stats = ImageStat.Stat(pil_image)
        
        # Mean colors
        mean_colors = {
            'red': float(stats.mean[0]),
            'green': float(stats.mean[1]),
            'blue': float(stats.mean[2])
        }
        
        # Standard deviation (color variance)
        std_colors = {
            'red': float(stats.stddev[0]),
            'green': float(stats.stddev[1]),
            'blue': float(stats.stddev[2])
        }
        
        # Dominant colors using K-means clustering
        dominant_colors = await self._extract_dominant_colors(img_array)
        
        # Color histogram
        hist_r = np.histogram(img_array[:, :, 0], bins=256, range=(0, 256))[0]
        hist_g = np.histogram(img_array[:, :, 1], bins=256, range=(0, 256))[0]
        hist_b = np.histogram(img_array[:, :, 2], bins=256, range=(0, 256))[0]
        
        # Calculate color distribution
        total_pixels = img_array.shape[0] * img_array.shape[1]
        color_distribution = {
            'red': float(np.sum(hist_r) / total_pixels),
            'green': float(np.sum(hist_g) / total_pixels),
            'blue': float(np.sum(hist_b) / total_pixels)
        }
        
        return {
            'mean_colors': mean_colors,
            'std_colors': std_colors,
            'dominant_colors': dominant_colors,
            'color_distribution': color_distribution,
        }
    
    async def _extract_dominant_colors(self, img_array: np.ndarray, 
                                     n_colors: int = 5) -> List[Dict[str, Any]]:
        """Extract dominant colors using K-means clustering."""
        if not SKLEARN_AVAILABLE:
            return []
        
        try:
            # Reshape image array
            pixels = img_array.reshape(-1, 3)
            
            # Sample pixels for efficiency
            if len(pixels) > 10000:
                indices = np.random.choice(len(pixels), 10000, replace=False)
                pixels = pixels[indices]
            
            # Apply K-means clustering
            unique_pixels = np.unique(pixels, axis=0)
            cluster_count = min(n_colors, len(unique_pixels))
            if cluster_count == 0:
                return []
            kmeans = KMeans(n_clusters=cluster_count, random_state=42, n_init=10)
            kmeans.fit(pixels)
            
            # Get cluster centers and labels
            colors = kmeans.cluster_centers_.astype(int)
            labels = kmeans.labels_
            
            # Calculate color frequencies
            unique, counts = np.unique(labels, return_counts=True)
            
            dominant_colors = []
            for i, (color, count) in enumerate(zip(colors, counts)):
                hex_color = f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"
                dominant_colors.append({
                    'rgb': color.tolist(),
                    'hex': hex_color,
                    'frequency': float(count / len(pixels)),
                    'cluster_id': int(unique[i])
                })
            
            # Sort by frequency
            dominant_colors.sort(key=lambda x: x['frequency'], reverse=True)
            
            return dominant_colors
            
        except Exception as e:
            logger.error(f"Error extracting dominant colors: {e}")
            return []
    
    async def _analyze_composition(self, img_array: np.ndarray) -> Dict[str, Any]:
        """Analyze image composition."""
        height, width = img_array.shape[:2]
        
        # Rule of thirds analysis
        rule_of_thirds = {
            'horizontal_lines': [height // 3, 2 * height // 3],
            'vertical_lines': [width // 3, 2 * width // 3],
        }
        
        # Center of mass (visual weight)
        if len(img_array.shape) == 3:
            # Color image - use luminance
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        # Calculate moments
        moments = cv2.moments(gray)
        if moments['m00'] != 0:
            center_x = int(moments['m10'] / moments['m00'])
            center_y = int(moments['m01'] / moments['m00'])
        else:
            center_x = width // 2
            center_y = height // 2
        
        # Calculate distance from center
        center_distance = np.sqrt((center_x - width/2)**2 + (center_y - height/2)**2)
        max_distance = np.sqrt((width/2)**2 + (height/2)**2)
        center_ratio = center_distance / max_distance if max_distance > 0 else 0
        
        # Symmetry analysis
        left_half = gray[:, :width//2]
        right_half = cv2.flip(gray[:, width//2:], 1)
        
        # Resize to match dimensions
        min_width = min(left_half.shape[1], right_half.shape[1])
        left_half = left_half[:, :min_width]
        right_half = right_half[:, :min_width]
        
        symmetry_score = 1 - np.mean(np.abs(left_half.astype(float) - right_half.astype(float))) / 255
        
        return {
            'rule_of_thirds': rule_of_thirds,
            'visual_center': {'x': center_x, 'y': center_y},
            'center_ratio': float(center_ratio),
            'symmetry_score': float(symmetry_score),
            'aspect_ratio': width / height,
        }
    
    async def _analyze_texture(self, img_array: np.ndarray) -> Dict[str, Any]:
        """Analyze texture properties of the image."""
        # Convert to grayscale if necessary
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        # Calculate texture features using Local Binary Patterns
        try:
            from skimage.feature import local_binary_pattern
            
            # LBP parameters
            radius = 1
            n_points = 8 * radius
            
            # Calculate LBP
            lbp = local_binary_pattern(gray, n_points, radius, method='uniform')
            
            # Calculate LBP histogram
            hist, _ = np.histogram(lbp.ravel(), bins=n_points + 2, range=(0, n_points + 2))
            hist = hist.astype(float)
            hist /= (hist.sum() + 1e-7)  # Normalize
            
            # Calculate texture statistics
            texture_energy = float(np.sum(hist**2))
            texture_entropy = float(-np.sum(hist * np.log(hist + 1e-7)))
            
        except ImportError:
            # Fallback: simple texture analysis
            # Calculate gradient magnitude
            grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)
            
            texture_energy = float(np.mean(gradient_magnitude))
            texture_entropy = 0.0  # Cannot calculate without LBP
        
        # Calculate standard deviation as texture measure
        texture_std = float(np.std(gray))
        
        return {
            'texture_energy': texture_energy,
            'texture_entropy': texture_entropy,
            'texture_std': texture_std,
        }
    
    async def _analyze_shapes(self, img_array: np.ndarray) -> Dict[str, Any]:
        """Analyze shapes and contours in the image."""
        # Convert to grayscale
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        # Apply edge detection
        edges = cv2.Canny(gray, 50, 150)
        
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Analyze contours
        contour_areas = [cv2.contourArea(contour) for contour in contours]
        contour_perimeters = [cv2.arcLength(contour, True) for contour in contours]
        
        # Calculate shape statistics
        if contour_areas:
            total_area = sum(contour_areas)
            avg_area = np.mean(contour_areas)
            max_area = max(contour_areas)
            
            # Calculate circularity (4π*area/perimeter²)
            circularities = []
            for area, perimeter in zip(contour_areas, contour_perimeters):
                if perimeter > 0:
                    circularity = 4 * np.pi * area / (perimeter ** 2)
                    circularities.append(circularity)
            
            avg_circularity = np.mean(circularities) if circularities else 0
        else:
            total_area = 0
            avg_area = 0
            max_area = 0
            avg_circularity = 0
        
        return {
            'num_contours': len(contours),
            'total_contour_area': float(total_area),
            'avg_contour_area': float(avg_area),
            'max_contour_area': float(max_area),
            'avg_circularity': float(avg_circularity),
        }
    
    async def _analyze_style(self, img_array: np.ndarray) -> Dict[str, Any]:
        """Analyze artistic style characteristics."""
        # Convert to grayscale
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        # Calculate image sharpness (Laplacian variance)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        sharpness = float(np.var(laplacian))
        
        # Calculate contrast (standard deviation)
        contrast = float(np.std(gray))
        
        # Calculate brightness (mean)
        brightness = float(np.mean(gray))
        
        # Calculate dynamic range
        min_val = float(np.min(gray))
        max_val = float(np.max(gray))
        dynamic_range = max_val - min_val
        
        # Calculate histogram distribution
        hist, _ = np.histogram(gray, bins=256, range=(0, 256))
        hist = hist.astype(float) / hist.sum()
        
        # Calculate histogram entropy
        hist_entropy = -np.sum(hist * np.log(hist + 1e-7))
        
        return {
            'sharpness': sharpness,
            'contrast': contrast,
            'brightness': brightness,
            'dynamic_range': dynamic_range,
            'histogram_entropy': float(hist_entropy),
        }
    
    async def compare_images(self, images: List[BlakeImage]) -> Dict[str, Any]:
        """Compare multiple images for similarity."""
        if len(images) < 2:
            return {'error': 'Need at least 2 images to compare'}
        
        try:
            # Extract features for each image
            features = []
            for image in images:
                if image.file_path and image.file_path.exists():
                    pil_image = Image.open(image.file_path)
                    img_array = np.array(pil_image)
                    
                    # Extract basic features
                    feature_vector = await self._extract_feature_vector(img_array)
                    features.append(feature_vector)
                else:
                    features.append(None)
            
            # Filter out None features
            valid_features = [f for f in features if f is not None]
            valid_images = [img for img, f in zip(images, features) if f is not None]
            
            if len(valid_features) < 2:
                return {'error': 'Need at least 2 valid images to compare'}
            
            # Calculate similarity matrix
            if SKLEARN_AVAILABLE:
                similarity_matrix = cosine_similarity(valid_features)
                
                # Find most similar pairs
                similarities = []
                for i in range(len(valid_images)):
                    for j in range(i + 1, len(valid_images)):
                        similarities.append({
                            'image1_id': valid_images[i].id,
                            'image2_id': valid_images[j].id,
                            'similarity': float(similarity_matrix[i][j])
                        })
                
                similarities.sort(key=lambda x: x['similarity'], reverse=True)
                
                return {
                    'similarity_matrix': similarity_matrix.tolist(),
                    'most_similar_pairs': similarities[:5],
                    'average_similarity': float(np.mean(similarity_matrix))
                }
            else:
                return {'error': 'scikit-learn not available for comparison'}
                
        except Exception as e:
            logger.error(f"Error comparing images: {e}")
            return {'error': str(e)}
    
    async def _extract_feature_vector(self, img_array: np.ndarray) -> np.ndarray:
        """Extract feature vector for image comparison."""
        # Convert to RGB if necessary
        if len(img_array.shape) == 3:
            pil_image = Image.fromarray(img_array)
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            img_array = np.array(pil_image)
        
        # Resize to standard size for comparison
        img_resized = cv2.resize(img_array, (64, 64))
        
        # Flatten and normalize
        feature_vector = img_resized.flatten().astype(float) / 255.0
        
        return feature_vector
