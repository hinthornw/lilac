<script lang="ts">
  import {
    infiniteQuerySelectRows,
    queryDatasetManifest,
    queryDatasetSchema,
    querySettings
  } from '$lib/queries/datasetQueries';
  import {getDatasetContext} from '$lib/stores/datasetStore';
  import {getDatasetViewContext, getSelectRowsOptions} from '$lib/stores/datasetViewStore';
  import {
    ITEM_SCROLL_CONTAINER_CTX_KEY,
    getHighlightedFields,
    getMediaFields
  } from '$lib/view_utils';
  import {InlineNotification, SkeletonText} from 'carbon-components-svelte';
  import {setContext} from 'svelte';
  import InfiniteScroll from 'svelte-infinite-scroll';
  import {writable} from 'svelte/store';
  import FilterPanel from './FilterPanel.svelte';
  import RowItem from './RowItem.svelte';

  const datasetViewStore = getDatasetViewContext();
  const datasetStore = getDatasetContext();

  $: manifest = queryDatasetManifest($datasetViewStore.namespace, $datasetViewStore.datasetName);

  $: schema = queryDatasetSchema($datasetViewStore.namespace, $datasetViewStore.datasetName);

  $: selectOptions = getSelectRowsOptions($datasetViewStore);

  $: settings = querySettings($datasetViewStore.namespace, $datasetViewStore.datasetName);

  $: selectRowsSchema = $datasetStore.selectRowsSchema;

  $: highlightedFields = getHighlightedFields($datasetViewStore.query, selectRowsSchema?.data);

  $: rows = infiniteQuerySelectRows(
    $datasetViewStore.namespace,
    $datasetViewStore.datasetName,
    selectOptions || {},
    selectRowsSchema?.isSuccess ? selectRowsSchema.data.schema : undefined
  );

  $: totalNumRows = $rows.data?.pages[0].total_num_rows;

  $: items = $rows.data?.pages.flatMap(x => x.rows);

  $: mediaFields = $settings.data
    ? getMediaFields($datasetStore.selectRowsSchema?.data?.schema, $settings.data)
    : [];
  // Pass the item scroll container to children so they can handle scroll events.
  let itemScrollContainer: HTMLDivElement | null = null;
  const writableStore = writable<HTMLDivElement | null>(itemScrollContainer);
  $: setContext(ITEM_SCROLL_CONTAINER_CTX_KEY, writableStore);
  $: writableStore.set(itemScrollContainer);
</script>

<FilterPanel {totalNumRows} manifest={$manifest.data} />

{#if $rows.isError}
  <InlineNotification
    lowContrast
    title="Could not fetch rows:"
    subtitle={$rows.error.body?.detail || $rows.error.message}
  />
{:else if selectRowsSchema?.isError}
  <InlineNotification
    lowContrast
    title="Could not fetch schema:"
    subtitle={selectRowsSchema.error.body?.detail || selectRowsSchema?.error.message}
  />
{:else if $rows?.isFetching || $schema.isFetching || selectRowsSchema?.isFetching || $settings.isFetching}
  <SkeletonText paragraph lines={3} />
{:else if $rows?.isSuccess && items && items.length === 0}
  <div class="mx-4 mt-8 w-full text-gray-600">No results.</div>
{/if}

{#if items && $schema.isSuccess && mediaFields != null}
  <div
    class="flex h-full w-full flex-col gap-y-10 overflow-y-scroll px-5 pb-32"
    bind:this={itemScrollContainer}
  >
    {#each items as row}
      <RowItem {row} {mediaFields} {highlightedFields} />
    {/each}
    {#if items.length > 0}
      <InfiniteScroll threshold={100} on:loadMore={() => $rows?.fetchNextPage()} />
    {/if}
  </div>
{/if}
