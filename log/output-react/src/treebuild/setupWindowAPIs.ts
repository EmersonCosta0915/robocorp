import { getOpts } from './options';
import { saveTreeState } from './persistTree';
import { getSampleContents } from './sample';
import { TreeBuilder } from './treeBuilder';
import {
  requestToHandler,
  sendEventToClient,
  nextMessageSeq,
  IEventMessage,
  ISetContentsRequest,
  IAppendContentsRequest,
  IUpdateLabelRequest,
  isInVSCode,
} from './vscodeComm';

let treeBuilder: TreeBuilder | undefined;

async function rebuildTreeAndStatusesFromOpts(): Promise<void> {
  treeBuilder = new TreeBuilder();
  treeBuilder.clearAndInitializeTree();
  await treeBuilder.addInitialContents();
}

function onClickReference(message: any) {
  let ev: IEventMessage = {
    type: 'event',
    seq: nextMessageSeq(),
    event: 'onClickReference',
  };
  ev['data'] = message;
  sendEventToClient(ev);
}

/**
 * Should be called to set the initial contents of the tree
 * as well as the current run id and label.
 */
export function setContents(msg: ISetContentsRequest): void {
  saveTreeState();
  const opts = getOpts();
  opts.runId = msg.runId;
  opts.initialContents = msg.initialContents;
  if (isInVSCode()) {
    opts.onClickReference = onClickReference;
  }
  opts.appendedContents = [];
  opts.allRunIdsToLabel = msg.allRunIdsToLabel;

  // TODO: Implement this.
  // rebuildRunSelection(opts.allRunIdsToLabel, opts.runId);
  rebuildTreeAndStatusesFromOpts();
}

export function setShowTime(showTime: boolean): void {
  getOpts().showTime = showTime;
}

export function setShowExpand(showExpand: boolean): void {
  getOpts().showExpand = showExpand;
}

export function appendContents(msg: IAppendContentsRequest): void {
  const opts = getOpts();
  if (opts.runId === msg.runId) {
    opts.appendedContents.push(msg.appendContents);
    if (treeBuilder !== undefined) {
      treeBuilder.onAppendedContents();
    }
  }
}

export function updateLabel(msg: IUpdateLabelRequest): void {
  const opts = getOpts();
  // TODO: Implement this.
  //   opts.allRunIdsToLabel[msg.runId] = msg.label;
  //   rebuildRunSelection(opts.allRunIdsToLabel, opts.runId);
}

function onChangedRun(selectedRun: any) {
  let ev: IEventMessage = {
    type: 'event',
    seq: nextMessageSeq(),
    event: 'onSetCurrentRunId',
  };
  ev['data'] = { runId: selectedRun };
  sendEventToClient(ev);
}

/**
 * Function sets up the globals in requestToHandler and window.
 */
export function setupGlobals() {
  requestToHandler['setContents'] = setContents;
  requestToHandler['appendContents'] = appendContents;
  requestToHandler['updateLabel'] = updateLabel;

  window.onChangedRun = onChangedRun;
  window.setContents = setContents;
  window.getSampleContents = getSampleContents;
}
