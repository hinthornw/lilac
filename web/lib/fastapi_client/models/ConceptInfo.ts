/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

import type { ConceptACL } from './ConceptACL';
import type { ConceptMetadata } from './ConceptMetadata';
import type { ConceptType } from './ConceptType';

/**
 * Information about a concept.
 */
export type ConceptInfo = {
    namespace: string;
    name: string;
    type: ConceptType;
    metadata: ConceptMetadata;
    drafts: Array<('main' | string)>;
    acls: ConceptACL;
};

