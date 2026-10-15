// Corrected figures may be displayed with a saved attempt from the same PDF.
// Keep its question text, answers and scoring snapshot intact in storage.
export function withCurrentPracticeImages(snapshot, current) {
  const original = snapshot?.sources?.paper, latest = current?.sources?.paper;
  if (!snapshot || !current || snapshot.book !== current.book || snapshot.test !== current.test ||
      snapshot.skill !== current.skill || !original?.sha256 || original.sha256 !== latest?.sha256 ||
      original.path !== latest.path) return {paper: snapshot, changed: false};

  const paper = structuredClone(snapshot);
  let changed = false;
  const copyImages = (target, source) => {
    if (!target || !source) return;
    const assets = source.assets || (source.asset ? [source.asset] : []);
    if (!assets.length || assets.some(a => !a || typeof a.asset !== 'string' || !a.sourcePdfPage)) return;
    const before = JSON.stringify({asset: target.asset, assets: target.assets});
    delete target.asset;
    delete target.assets;
    if (source.assets) target.assets = structuredClone(source.assets);
    else target.asset = structuredClone(source.asset);
    if (JSON.stringify({asset: target.asset, assets: target.assets}) !== before) changed = true;
  };
  const match = (items, item) => (items || []).find(candidate =>
    item.id ? candidate.id === item.id : item.number != null ? candidate.number === item.number : candidate.part === item.part);
  if (paper.skill === 'writing') {
    for (const task of paper.tasks || []) copyImages(task, match(current.tasks, task));
  } else if (paper.skill === 'reading') {
    for (const passage of paper.passages || []) {
      const source = match(current.passages, passage);
      for (const group of passage.groups || []) copyImages(group, match(source?.groups, group));
    }
  } else {
    for (const part of paper.parts || []) {
      const source = match(current.parts, part);
      copyImages(part, source);
      copyImages(part.cueCard, source?.cueCard);
    }
  }
  return {paper: changed ? paper : snapshot, changed};
}
