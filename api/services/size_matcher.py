"""
Сервис подбора размеров на основе параметров пользователя
"""
import logging
from typing import Optional, Dict, List, Tuple

logger = logging.getLogger(__name__)


class SizeMatcherService:
    """Сервис для подбора размера одежды"""

    ALL_PARAMS = [
        'russian_size', 'shoulder_length', 'back_width', 'sleeve_length',
        'back_length', 'chest', 'waist', 'hips', 'pants_length',
        'waist_girth', 'rise_height', 'back_rise_height'
    ]

    def _parse_size_range(self, size_val: any) -> Tuple[Optional[int], Optional[int]]:
        """Парсит значение размера, которое может быть числом или диапазоном '42-44'."""
        if size_val is None:
            return None, None
        s = str(size_val).strip()
        try:
            if '-' in s:
                parts = s.split('-')
                return int(parts[0]), int(parts[1])
            else:
                val = int(s)
                return val, val
        except (ValueError, TypeError):
            return None, None

    def _get_param_boundaries(self, size_table: List[Dict]) -> Dict:
        """
        Найти абсолютные минимальные и максимальные значения для каждого параметра
        в таблице размеров, а также соответствующие им размеры.
        """
        boundaries = {}
        for param in self.ALL_PARAMS:
            min_val, max_val = float('inf'), float('-inf')
            min_size, max_size = None, None

            for row in size_table:
                if param == 'russian_size':
                    p_min, p_max = self._parse_size_range(row.get('russian_size'))
                else:
                    p_min = row.get(f'{param}_min')
                    p_max = row.get(f'{param}_max')

                if p_min is not None and p_min < min_val:
                    min_val = p_min
                    min_size = row.get('size')

                if p_max is not None and p_max > max_val:
                    max_val = p_max
                    max_size = row.get('size')

            if min_size and max_size:
                boundaries[param] = {
                    'abs_min': min_val,
                    'abs_max': max_val,
                    'min_size': min_size,
                    'max_size': max_size
                }

        return boundaries

    def recommend_size(
        self,
        user_measurements: Dict[str, any],
        size_table: List[Dict],
        available_sizes: List[str]
    ) -> Dict:
        """Подобрать размер на основе параметров пользователя."""
        if not user_measurements:
            return {
                "success": False,
                "message": "📐 Укажи свои параметры, чтобы получить рекомендацию по размеру",
                "confidence": "none",
                "recommended_size": None,
                "alternative_size": None,
                "details": {"reason": "no_measurements"}
            }

        if not size_table:
            return {
                "success": False,
                "message": "⚠️ Таблица размеров не найдена",
                "confidence": "none",
                "recommended_size": None,
                "alternative_size": None,
                "details": {"reason": "no_size_table"}
            }

        filtered_table = [row for row in size_table if row.get('size') in available_sizes]

        if not filtered_table:
            return {
                "success": False,
                "message": "⚠️ Не удалось подобрать размер. Рекомендуем уточнить у продавца",
                "confidence": "none",
                "recommended_size": None,
                "alternative_size": None,
                "details": {"reason": "no_available_sizes"}
            }

        size_scores = {row['size']: {'score': 0, 'matched_params': []} for row in filtered_table}
        param_boundaries = self._get_param_boundaries(filtered_table)
        max_possible_score = 0

        for param, user_val in user_measurements.items():
            if user_val is None or user_val == '' or param not in self.ALL_PARAMS:
                continue

            boundaries = param_boundaries.get(param)
            if not boundaries:
                continue

            max_possible_score += 1

            try:
                user_val_num = float(user_val)
            except (ValueError, TypeError):
                continue

            if user_val_num > boundaries['abs_max']:
                max_size = boundaries['max_size']
                if max_size in size_scores:
                    size_scores[max_size]['score'] += 1
                    size_scores[max_size]['matched_params'].append(param)
                continue

            if user_val_num < boundaries['abs_min']:
                min_size = boundaries['min_size']
                if min_size in size_scores:
                    size_scores[min_size]['score'] += 1
                    size_scores[min_size]['matched_params'].append(param)
                continue

            for row in filtered_table:
                if param == 'russian_size':
                    min_val, max_val = self._parse_size_range(row.get('russian_size'))
                else:
                    min_val = row.get(f'{param}_min')
                    max_val = row.get(f'{param}_max')

                if min_val is not None and max_val is not None:
                    if min_val <= user_val_num <= max_val:
                        size_scores[row['size']]['score'] += 1
                        size_scores[row['size']]['matched_params'].append(param)
                        break

        if max_possible_score == 0:
            return {
                "success": False,
                "message": "⚠️ Нет общих параметров для сравнения. Заполните больше данных",
                "confidence": "none",
                "recommended_size": None,
                "alternative_size": None,
                "details": {"reason": "no_common_params"}
            }

        sorted_scores = sorted(size_scores.items(), key=lambda item: item[1]['score'], reverse=True)

        if not sorted_scores or sorted_scores[0][1]['score'] == 0:
            return {
                "success": False,
                "message": "⚠️ Не удалось подобрать размер. Рекомендуем уточнить у продавца",
                "confidence": "none",
                "recommended_size": None,
                "alternative_size": None,
                "details": {"reason": "no_match"}
            }

        best_match_size, best_match_data = sorted_scores[0]
        score = best_match_data['score']

        alternative_size = None
        if len(sorted_scores) > 1 and sorted_scores[1][1]['score'] >= max(1, score - 1):
            alternative_size = sorted_scores[1][0]

        confidence_ratio = score / max_possible_score
        if confidence_ratio == 1.0:
            confidence = "high"
            message = f"✅ Рекомендуемый размер: {best_match_size}"
        elif confidence_ratio >= 0.7:
            confidence = "medium"
            message = f"✅ Рекомендуемый размер: {best_match_size}"
        else:
            confidence = "low"
            message = f"⚠️ Возможный размер: {best_match_size}, но рекомендуем уточнить у продавца"

        if alternative_size and best_match_size != alternative_size:
            message += f" (также может подойти {alternative_size})"

        return {
            "success": True,
            "recommended_size": best_match_size,
            "alternative_size": alternative_size if best_match_size != alternative_size else None,
            "confidence": confidence,
            "message": message,
            "details": {
                "score": score,
                "max_possible_score": max_possible_score,
                "matched_parameters": list(set(best_match_data['matched_params']))
            }
        }


# Singleton instance
size_matcher_service = SizeMatcherService()
