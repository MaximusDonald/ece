import * as React from 'react';
import { CorpusExplorerView } from '@/components/corpus/CorpusExplorerView';
import { LoadingState } from '@/components/ui/feedback';

export default function AdminCorpusExplorerPage() {
  return (
    <React.Suspense fallback={<LoadingState label="Chargement du Corpus Souverain…" />}>
      <CorpusExplorerView adminContext />
    </React.Suspense>
  );
}
