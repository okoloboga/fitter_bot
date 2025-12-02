"""
Сервис подбора размеров на основе параметров пользователя
"""
import logging
from typing import Optional, Dict, List, Tuple

logger = logging.getLogger(__name__)


class SizeMatcherService:
    """Сервис для подбора размера одежды"""

    def recommend_size(
        self,
        user_measurements: Dict[str, int],
        size_table: List[Dict],
        available_sizes: List[str]
    ) -> Dict:
        """
        Подобрать размер на основе параметров пользователя

        Args:
            user_measurements: Параметры пользователя (height, chest, waist, hips)
            size_table: Таблица размеров из Google Sheets
            available_sizes: Доступные размеры для товара

        Returns:
            Dict с рекомендацией размера
        """
        if not user_measurements:
            return {
                "success": False,
                "message": "📐 Укажи свои параметры, чтобы получить рекомендацию по размеру",
                "reason": "no_measurements",
                "recommended_size": None,
                "alternative_size": None,
                "confidence": "none"
            }

        if not size_table:
            return {
                "success": False,
                "message": "⚠️ Таблица размеров не найдена",
                "reason": "no_size_table",
                "recommended_size": None,
                "alternative_size": None,
                "confidence": "none"
            }

        # Фильтруем таблицу размеров по доступным размерам
        filtered_table = [row for row in size_table if row['size'] in available_sizes]

        if not filtered_table:
            return {
                "success": False,
                "message": "⚠️ Не удалось подобрать размер. Рекомендуем уточнить у продавца",
                "reason": "no_available_sizes",
                "recommended_size": None,
                "alternative_size": None,
                "confidence": "none"
            }

        # Подсчет совпадений для каждого размера
        size_scores = []

        for row in filtered_table:
            score, matched_params = self._calculate_match_score(user_measurements, row)
            size_scores.append({
                'size': row['size'],
                'score': score,
                'matched_params': matched_params,
                'row': row
            })

        # Сортируем по количеству совпадений
        size_scores.sort(key=lambda x: x['score'], reverse=True)

        if not size_scores or size_scores[0]['score'] == 0:
            return {
                "success": False,
                "message": "⚠️ Не удалось подобрать размер. Рекомендуем уточнить у продавца",
                "reason": "no_match",
                "recommended_size": None,
                "alternative_size": None,
                "confidence": "none"
            }

        # Лучший размер
        best_match = size_scores[0]
        recommended_size = best_match['size']
        score = best_match['score']

        # Подсчитываем максимально возможный score (учитываем только не-NULL параметры)
        max_possible_score = len([p for p in ['height', 'chest', 'waist', 'hips']
                                 if best_match['row'].get(f'{p}_min') is not None])

        # Альтернативный размер (если есть)
        alternative_size = None
        if len(size_scores) > 1 and size_scores[1]['score'] >= max_possible_score - 1:
            alternative_size = size_scores[1]['size']

        # Определяем уровень confidence
        if score == max_possible_score:
            confidence = "high"
            if alternative_size:
                message = f"✅ Рекомендуемый размер: {recommended_size} (также может подойти {alternative_size})"
            else:
                message = f"✅ Рекомендуемый размер: {recommended_size}"
        elif score >= max_possible_score - 1:
            confidence = "medium"
            if alternative_size:
                message = f"✅ Рекомендуемый размер: {recommended_size} (также может подойти {alternative_size})"
            else:
                message = f"✅ Рекомендуемый размер: {recommended_size}"
        else:
            confidence = "low"
            message = f"⚠️ Возможный размер: {recommended_size}, но рекомендуем уточнить у продавца"

        return {
            "success": True,
            "recommended_size": recommended_size,
            "alternative_size": alternative_size,
            "confidence": confidence,
            "message": message,
            "details": {
                "score": score,
                "max_possible_score": max_possible_score,
                "matched_parameters": best_match['matched_params']
            }
        }

    def _calculate_match_score(self, user_measurements: Dict[str, int], size_row: Dict) -> Tuple[int, List[str]]:
        """
        Подсчитать количество совпадающих параметров

        Returns:
            Tuple (score, matched_parameters)
        """
        score = 0
        matched_params = []

        params_to_check = ['height', 'chest', 'waist', 'hips']

        for param in params_to_check:
            min_val = size_row.get(f'{param}_min')
            max_val = size_row.get(f'{param}_max')
            user_val = user_measurements.get(param)

            # Если параметр не задан в таблице размеров, пропускаем
            if min_val is None or max_val is None:
                continue

            # Если параметр пользователя попадает в диапазон
            if user_val and min_val <= user_val <= max_val:
                score += 1
                matched_params.append(param)

        return score, matched_params


# Singleton instance
size_matcher_service = SizeMatcherService()
