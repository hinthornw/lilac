/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

/**
 * The result of a stats() query.
 */
export type StatsResult = {
    path: Array<string>;
    total_count: number;
    approx_count_distinct: number;
    min_val?: (number | string);
    max_val?: (number | string);
    avg_text_length?: number;
};

