<script lang="ts">
  /**
   * Component that renders string spans as an absolute positioned
   * layer, meant to be rendered on top of the source text.
   */
  import {editConceptMutation} from '$lib/queries/conceptQueries';
  import type {DatasetState} from '$lib/stores/datasetStore';
  import type {DatasetViewStore} from '$lib/stores/datasetViewStore';
  import {getNotificationsContext} from '$lib/stores/notificationsStore';
  import {ITEM_SCROLL_CONTAINER_CTX_KEY, mergeSpans, type MergedSpan} from '$lib/view_utils';
  import {
    L,
    getValueNodes,
    pathIncludes,
    pathIsEqual,
    serializePath,
    type ConceptSignal,
    type LilacValueNode,
    type LilacValueNodeCasted,
    type Path
  } from '$lilac';
  import {Button} from 'carbon-components-svelte';
  import {ArrowDown, ArrowUp} from 'carbon-icons-svelte';
  import {getContext} from 'svelte';
  import SvelteMarkdown from 'svelte-markdown';
  import type {Writable} from 'svelte/store';
  import {hoverTooltip} from '../common/HoverTooltip';
  import {spanClick} from './SpanClick';
  import {spanHover} from './SpanHover';
  import type {SpanDetails} from './StringSpanDetails.svelte';
  import {LABELED_TEXT_COLOR, colorFromOpacity} from './colors';
  import {
    getRenderSpans,
    getSnippetSpans,
    type RenderSpan,
    type SpanValueInfo
  } from './spanHighlight';

  export let text: string;
  // The full row item.
  export let row: LilacValueNode;
  // Path of the spans for this item to render.
  export let spanPaths: Path[];
  export let path: Path | undefined = undefined;

  // Information about each value under span paths to render.
  export let valuePaths: SpanValueInfo[];
  export let markdown = false;
  export let embeddings: string[];

  // When defined, enables semantic search on spans.
  export let datasetViewStore: DatasetViewStore | undefined = undefined;
  export let datasetStore: DatasetState | undefined = undefined;

  const spanHoverOpacity = 0.9;

  let pathToSpans: {
    [path: string]: LilacValueNodeCasted<'string_span'>[];
  };
  $: {
    pathToSpans = {};
    spanPaths.forEach(sp => {
      const valueNodes = getValueNodes(row, sp);
      pathToSpans[serializePath(sp)] = valueNodes.filter(
        v => pathIncludes(L.path(v), path) || path == null
      ) as LilacValueNodeCasted<'string_span'>[];
    });
  }

  let spanPathToValueInfos: Record<string, SpanValueInfo[]> = {};
  $: {
    spanPathToValueInfos = {};
    for (const valuePath of valuePaths) {
      const spanPathStr = serializePath(valuePath.spanPath);
      if (spanPathToValueInfos[spanPathStr] == null) {
        spanPathToValueInfos[spanPathStr] = [];
      }
      spanPathToValueInfos[spanPathStr].push(valuePath);
    }
  }

  // Merge all the spans for different features into a single span array.
  $: mergedSpans = mergeSpans(text, pathToSpans);

  // Span hover tracking.
  let pathsHovered: Set<string> = new Set();
  const spanMouseEnter = (renderSpan: RenderSpan) => {
    renderSpan.paths.forEach(path => pathsHovered.add(path));
    pathsHovered = pathsHovered;
  };
  const spanMouseLeave = (renderSpan: RenderSpan) => {
    renderSpan.paths.forEach(path => pathsHovered.delete(path));
    pathsHovered = pathsHovered;
  };
  $: renderSpans = getRenderSpans(mergedSpans, spanPathToValueInfos, pathsHovered);

  // Map each of the paths to their render spans so we can highlight neighbors on hover when there
  // is overlap.
  let pathToRenderSpans: {[pathStr: string]: Array<MergedSpan>} = {};
  $: {
    pathToRenderSpans = {};
    for (const renderSpan of mergedSpans) {
      for (const path of renderSpan.paths) {
        pathToRenderSpans[path] = pathToRenderSpans[path] || [];
        pathToRenderSpans[path].push(renderSpan);
      }
    }
  }

  const getSpanDetails = (span: RenderSpan): SpanDetails => {
    // Get all the render spans that include this path so we can join the text.
    const spansUnderClick = renderSpans.filter(renderSpan =>
      renderSpan.paths.some(s =>
        (span?.paths || []).some(selectedSpanPath => pathIsEqual(selectedSpanPath, s))
      )
    );
    const fullText = spansUnderClick.map(s => s.text).join('');
    const spanDetails: SpanDetails = {
      conceptName: null,
      conceptNamespace: null,
      text: fullText
    };
    // Find the concepts for the selected spans. For now, we select just the first concept.
    for (const spanPath of Object.keys(span.originalSpans)) {
      const conceptValues = (spanPathToValueInfos[spanPath] || []).filter(
        v => v.type === 'concept_score'
      );
      for (const conceptValue of conceptValues) {
        // Only use the first concept. We will later support multiple concepts.
        const signal = conceptValue.signal as ConceptSignal;
        spanDetails.conceptName = signal.concept_name;
        spanDetails.conceptNamespace = signal.namespace;
        break;
      }
    }
    return spanDetails;
  };
  const conceptEdit = editConceptMutation();
  const addConceptLabel = (
    conceptNamespace: string,
    conceptName: string,
    text: string,
    label: boolean
  ) => {
    if (!conceptName || !conceptNamespace)
      throw Error('Label could not be added, no active concept.');
    $conceptEdit.mutate([conceptNamespace, conceptName, {insert: [{text, label}]}]);
  };

  let isExpanded = false;
  // Snippets.
  $: ({snippetSpans, someSnippetsHidden} = getSnippetSpans(renderSpans, isExpanded));

  let itemScrollContainer = getContext<Writable<HTMLDivElement | null>>(
    ITEM_SCROLL_CONTAINER_CTX_KEY
  );

  const findSimilar = (embedding: string, text: string) => {
    if (datasetViewStore == null || path == null) return;
    datasetViewStore.addSearch({
      path: [serializePath(path)],
      type: 'semantic',
      query: text,
      embedding
    });
  };

  const notificationStore = getNotificationsContext();
</script>

<div class="relative overflow-x-hidden text-ellipsis whitespace-break-spaces py-4">
  {#each snippetSpans as snippetSpan}
    {@const renderSpan = snippetSpan.renderSpan}
    {#if snippetSpan.isShown}
      <span
        use:spanHover={{
          namedValues: renderSpan.namedValues,
          isHovered: renderSpan.isFirstHover,
          spansHovered: pathsHovered,
          itemScrollContainer: $itemScrollContainer
        }}
        use:spanClick={{
          details: () => getSpanDetails(renderSpan),
          // Disable similarity search when there's no dataset store.
          findSimilar: datasetStore != null ? findSimilar : null,
          embeddings,
          addConceptLabel,
          addNotification:
            notificationStore != null ? notificationStore.addNotification : () => null,
          disabled: renderSpan.paths.length === 0 || embeddings.length === 0
        }}
        class="hover:cursor-poiner highlight-span break-words text-sm leading-5"
        class:hover:cursor-pointer={spanPaths.length > 0}
        class:font-bold={renderSpan.isBlackBolded}
        class:font-medium={renderSpan.isHighlightBolded && !renderSpan.isBlackBolded}
        style:color={renderSpan.isHighlightBolded && !renderSpan.isBlackBolded
          ? LABELED_TEXT_COLOR
          : ''}
        style:background-color={!renderSpan.isHovered
          ? renderSpan.backgroundColor
          : colorFromOpacity(spanHoverOpacity)}
        on:mouseenter={() => spanMouseEnter(renderSpan)}
        on:mouseleave={() => spanMouseLeave(renderSpan)}
      >
        {#if markdown}
          <SvelteMarkdown source={renderSpan.snippetText} />
        {:else}
          {renderSpan.snippetText}
        {/if}
      </span>
    {:else if snippetSpan.isEllipsis}<span
        use:hoverTooltip={{
          text: 'Some text was hidden to improve readability. \nClick "Show all" to show the entire document.'
        }}
        class="highlight-span text-sm leading-5">...</span
      >{#if snippetSpan.hasNewline}<span><br /></span>{/if}
    {/if}
  {/each}
  {#if someSnippetsHidden || isExpanded}
    <div class="flex flex-row justify-center">
      <div class="w-30 mt-2 rounded border border-neutral-300 text-center">
        {#if !isExpanded}
          <Button
            size="small"
            class="w-full"
            kind="ghost"
            icon={ArrowDown}
            on:click={() => (isExpanded = true)}
          >
            Show all
          </Button>
        {:else}
          <Button
            size="small"
            class="w-full"
            kind="ghost"
            icon={ArrowUp}
            on:click={() => (isExpanded = false)}
          >
            Hide excess
          </Button>
        {/if}
      </div>
    </div>
  {/if}
</div>

<style lang="postcss">
  .highlight-span {
    /** Add a tiny bit of padding so that the hover doesn't flicker between rows. */
    padding-top: 1.5px;
    padding-bottom: 1.5px;
  }
  :global(.highlight-span pre) {
    @apply bg-slate-200;
    @apply text-sm;
  }
  :global(.highlight-span p),
  :global(.highlight-span pre) {
    @apply my-3;
  }
  :global(.highlight-span p:first-child) {
    @apply !inline;
  }
  :global(.highlight-span p:last-child) {
    @apply !inline;
  }
  :global(.highlight-span p),
  :global(.highlight-span h1) {
    background-color: inherit;
  }
  :global(.highlight-span p) {
    @apply text-sm;
    font-weight: inherit;
  }
</style>
