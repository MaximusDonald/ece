import * as React from 'react';
import { CorpusExplorerView } from '@/components/corpus/CorpusExplorerView';
import { LoadingState } from '@/components/ui/feedback';

export default function CorpusLibraryPage() {
  return (
    <React.Suspense fallback={<LoadingState label="Chargement de la bibliothèque des Codes…" />}>
      <CorpusExplorerView />
    </React.Suspense>
  );
}
