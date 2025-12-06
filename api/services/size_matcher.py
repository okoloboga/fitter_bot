"""
Сервис подбора размеров на основе параметров пользователя
"""
import logging
from typing import Optional, Dict, List, Tuple

logger = logging.getLogger(__name__)


class SizeMatcherService:
    """Сервис для подбора размера одежды"""

    # Список всех возможных параметров для сравнения
    ALL_PARAMS = [
        'russian_size',
        'shoulder_length',
        'back_width',
        'sleeve_length',
        'back_length',
        'chest',
        'waist',
        'hips',
        'pants_length',
        'waist_girth',
        'rise_height',
        'back_rise_height'
    ]

    def recommend_size(
        self,
        user_measurements: Dict[str, any],
        size_table: List[Dict],
        available_sizes: List[str]
    ) -> Dict:
        """
        Подобрать размер на основе параметров пользователя

        Args:
            user_measurements: Параметры пользователя (могут быть не все)
            size_table: Таблица размеров из Google Sheets
            available_sizes: Доступные размеры для товара

        Returns:
            Dict с рекомендацией размера
        """
        logger.warning("--- Starting Size Recommendation ---")
        logger.info(f"User Measurements: {user_measurements}")
        logger.info(f"Available Sizes for Product: {available_sizes}")
        logger.info(f"Received Size Table with {len(size_table)} rows.")

        if not user_measurements:
            logger.warning("No user measurements provided.")
            return {
                "success": False,
                "message": "📐 Укажи свои параметры, чтобы получить рекомендацию по размеру",
                "reason": "no_measurements",
                "recommended_size": None,
                "alternative_size": None,
                "confidence": "none"
            }

        if not size_table:
            logger.warning("Size table is empty.")
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
        logger.info(f"Filtered size table contains {len(filtered_table)} rows for available sizes.")

        if not filtered_table:
            logger.warning("Filtered size table is empty. No matching sizes found in the size table for the available sizes.")
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
        logger.info("--- Calculating Scores for Each Size ---")
        for row in filtered_table:
            score, matched_params = self._calculate_match_score(user_measurements, row)
            logger.info(f"Size: {row.get('size')}, Score: {score}, Matched Params: {matched_params}")
            size_scores.append({
                'size': row['size'],
                'score': score,
                'matched_params': matched_params,
                'row': row
            })

        # Сортируем по количеству совпадений
        size_scores.sort(key=lambda x: x['score'], reverse=True)
        logger.info(f"Sorted Scores: {[ (s['size'], s['score']) for s in size_scores ]}")

        if not size_scores or size_scores[0]['score'] == 0:
            logger.warning("No size got a score greater than 0.")
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

        # Подсчитываем максимально возможный score (параметры, которые есть и у пользователя и в таблице)
        max_possible_score = self._get_max_possible_score(user_measurements, best_match['row'])
        logger.info(f"Best match: {recommended_size} with score {score}. Max possible score: {max_possible_score}")

        if max_possible_score == 0:
            logger.warning("Max possible score is 0. No common parameters between user and size table.")
            return {
                "success": False,
                "message": "⚠️ Нет общих параметров для сравнения. Рекомендуем заполнить больше данных",
                "reason": "no_common_params",
                "recommended_size": None,
                "alternative_size": None,
                "confidence": "none"
            }

        # Альтернативный размер (если есть)
        alternative_size = None
        if len(size_scores) > 1 and size_scores[1]['score'] >= max(1, max_possible_score - 1):
            alternative_size = size_scores[1]['size']

        # Определяем уровень confidence
        confidence_ratio = score / max_possible_score if max_possible_score > 0 else 0
        
        if confidence_ratio == 1.0:
            confidence = "high"
            if alternative_size:
                message = f"✅ Рекомендуемый размер: {recommended_size} (также может подойти {alternative_size})"
            else:
                message = f"✅ Рекомендуемый размер: {recommended_size}"
        elif confidence_ratio >= 0.7:
            confidence = "medium"
            if alternative_size:
                message = f"✅ Рекомендуемый размер: {recommended_size} (также может подойти {alternative_size})"
            else:
                message = f"✅ Рекомендуемый размер: {recommended_size}"
        else:
            confidence = "low"
            message = f"⚠️ Возможный размер: {recommended_size}, но рекомендуем уточнить у продавца"

        logger.info(f"Final Recommendation: size={recommended_size}, alt_size={alternative_size}, confidence={confidence_ratio:.2f}")
        logger.info("--- End of Size Recommendation ---")

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

    def _calculate_match_score(self, user_measurements: Dict[str, any], size_row: Dict) -> Tuple[int, List[str]]:
        """
        Подсчитать количество совпадающих параметров
        Сравниваются только те параметры, которые есть И у пользователя И в таблице размеров

        Returns:
            Tuple (score, matched_parameters)
        """
        score = 0
        matched_params = []

        for param in self.ALL_PARAMS:
            user_val = user_measurements.get(param)

            # Если параметра нет у пользователя, пропускаем
            if user_val is None or user_val == '':
                continue

            # Для строковых параметров (например russian_size) - точное совпадение
            if param == 'russian_size':
                table_val = size_row.get('russian_size')
                if self._check_russian_size_match(user_val, table_val):
                    score += 1
                    matched_params.append(param)
                continue

            # Для числовых параметров - проверка диапазона
            min_val = size_row.get(f'{param}_min')
            max_val = size_row.get(f'{param}_max')

            # Если параметр не задан в таблице размеров, пропускаем
            if min_val is None or max_val is None:
                continue

            # Если параметр пользователя попадает в диапазон
            try:
                user_val_int = int(user_val)
                if min_val <= user_val_int <= max_val:
                    score += 1
                    matched_params.append(param)
            except (ValueError, TypeError):
                # Если не удалось преобразовать в число, пропускаем
                continue

        return score, matched_params

    def _check_russian_size_match(self, user_size: any, table_size: any) -> bool:
        """
        Проверяет совпадение российского размера, поддерживая диапазоны.
        Пример: user_size="42", table_size="42-44" -> True
        """
        if user_size is None or table_size is None:
            return False

        try:
            user_size_val = int(str(user_size).strip())
            table_size_str = str(table_size).strip()

            # Если в таблице диапазон (e.g., "42-44")
            if '-' in table_size_str:
                parts = table_size_str.split('-')
                if len(parts) == 2:
                    start = int(parts[0].strip())
                    end = int(parts[1].strip())
                    return start <= user_size_val <= end
            # Если в таблице одно число
            else:
                return user_size_val == int(table_size_str)
        except (ValueError, TypeError):
            # Если не удалось преобразовать в числа, сравниваем как строки
            return str(user_size).strip().lower() == str(table_size).strip().lower()

        return False

    def _get_max_possible_score(self, user_measurements: Dict[str, any], size_row: Dict) -> int:
        """
        Подсчитать максимально возможный score - количество параметров,
        которые есть И у пользователя И в таблице размеров
        """
        max_score = 0

        for param in self.ALL_PARAMS:
            user_val = user_measurements.get(param)

            # Если параметра нет у пользователя, пропускаем
            if user_val is None or user_val == '':
                continue

            # Для строковых параметров
            if param == 'russian_size':
                table_val = size_row.get('russian_size')
                if table_val:
                    max_score += 1
                continue

            # Для числовых параметров
            min_val = size_row.get(f'{param}_min')
            max_val = size_row.get(f'{param}_max')

            if min_val is not None and max_val is not None:
                max_score += 1

        return max_score


# Singleton instance
size_matcher_service = SizeMatcherService()
