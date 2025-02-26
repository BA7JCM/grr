import {NestedTreeControl} from '@angular/cdk/tree';
import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  Input,
  OnChanges,
  SimpleChanges,
} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatIconModule} from '@angular/material/icon';
import {MatTreeModule} from '@angular/material/tree';

import {Process} from '../../../lib/api/api_interfaces';
import {createOptionalDate} from '../../../lib/api_translation/primitive';
import {TimestampModule} from '../../timestamp/module';

interface ProcessNode extends Process {
  readonly pid: number;
  readonly date?: Date;
  readonly children: ProcessNode[];
}

function newNode(process: Process): ProcessNode {
  return {
    ...process,
    pid: process.pid!,
    date: createOptionalDate(process.ctime),
    children: [],
  };
}

function toTrees(processes: readonly Process[]): ProcessNode[] {
  const rootNodes = new Set(processes.map(newNode));
  const nodes = new Map(Array.from(rootNodes.values()).map((p) => [p.pid, p]));

  for (const node of nodes.values()) {
    if (node.ppid === undefined) {
      continue;
    }

    const parent = nodes.get(node.ppid);
    if (parent === undefined) {
      continue;
    }

    parent.children.push(node);
    rootNodes.delete(node);
  }

  return Array.from(rootNodes);
}

/** Component to show a tree-view of operating system processes. */
@Component({
  selector: 'app-process-view',
  templateUrl: './process_view.ng.html',
  styleUrls: ['./process_view.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatIconModule,
    MatTreeModule,
    TimestampModule,
  ],
})
export class ProcessView implements OnChanges {
  protected readonly treeControl = new NestedTreeControl<ProcessNode, number>(
    (node) => node.children,
    {trackBy: (node) => node.pid},
  );

  @Input() data: Process[] | null = null;

  protected processNodes: ProcessNode[] = [];

  ngOnInit() {
    if (!this.data) {
      return;
    }

    this.processNodes = toTrees(this.data);
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes['data'].currentValue !== null) {
      this.processNodes = toTrees(changes['data'].currentValue);
    }
  }

  protected hasChild(index: number, process: ProcessNode): boolean {
    return process.children.length > 0;
  }
}
