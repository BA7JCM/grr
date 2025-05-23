import {ChangeDetectionStrategy, Component, ViewChild} from '@angular/core';
import {FormControl} from '@angular/forms';
import {ActivatedRoute, Router} from '@angular/router';
import {BehaviorSubject, Observable, combineLatest, of} from 'rxjs';
import {
  filter,
  map,
  startWith,
  switchMap,
  takeUntil,
  tap,
} from 'rxjs/operators';

import {
  ApiFlowReference,
  ApiHuntReference,
} from '../../../lib/api/api_interfaces';
import {FlowWithDescriptor} from '../../../lib/models/flow';
import {Hunt, getHuntTitle} from '../../../lib/models/hunt';
import {isNonNull, isNull} from '../../../lib/preconditions';
import {observeOnDestroy} from '../../../lib/reactive';
import {HuntApprovalLocalStore} from '../../../store/hunt_approval_local_store';
import {NewHuntLocalStore} from '../../../store/new_hunt_local_store';
import {UserGlobalStore} from '../../../store/user_global_store';
import {ApprovalCard, ApprovalParams} from '../../approval_card/approval_card';

import {ClientsForm} from './clients_form/clients_form';
import {OutputPluginsForm} from './output_plugins_form/output_plugins_form';
import {ParamsForm} from './params_form/params_form';

/**
 * Provides the new hunt creation page.
 */
@Component({
  standalone: false,
  templateUrl: './new_hunt.ng.html',
  styleUrls: ['./new_hunt.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [NewHuntLocalStore, HuntApprovalLocalStore],
})
export class NewHunt {
  @ViewChild('clientsForm', {static: false}) clientsForm!: ClientsForm;
  @ViewChild('paramsForm', {static: false}) paramsForm!: ParamsForm;
  @ViewChild('outputPluginsForm', {static: false})
  outputPluginsForm!: OutputPluginsForm;
  @ViewChild('approvalCard', {static: false}) approvalCard?: ApprovalCard;

  readonly flowWithDescriptor$: Observable<FlowWithDescriptor | null>;
  readonly originalHunt$: Observable<Hunt | null>;
  protected originalHuntRef: ApiHuntReference | undefined = undefined;
  protected originalFlowRef: ApiFlowReference | undefined = undefined;

  readonly huntId$;
  readonly huntApprovalRequired$;
  protected readonly latestApproval$;
  protected readonly huntApprovalRoute$;
  private readonly approvalParams$;
  protected readonly requestApprovalStatus$;
  protected hasOriginInput: boolean | undefined = undefined;

  titleControl;

  readonly ngOnDestroy;

  protected readonly huntsOverviewRoute;

  readonly hasOrigin$;

  readonly canCreateHunt$;

  constructor(
    private readonly route: ActivatedRoute,
    private readonly newHuntLocalStore: NewHuntLocalStore,
    private readonly huntApprovalLocalStore: HuntApprovalLocalStore,
    private readonly router: Router,
    private readonly userGlobalStore: UserGlobalStore,
  ) {
    this.flowWithDescriptor$ = this.newHuntLocalStore.flowWithDescriptor$;
    this.originalHunt$ = this.newHuntLocalStore.originalHunt$;
    this.huntId$ = this.newHuntLocalStore.huntId$;
    this.huntApprovalRequired$ = this.userGlobalStore.currentUser$.pipe(
      map((user) => user.huntApprovalRequired),
    );
    this.latestApproval$ = this.huntApprovalLocalStore.latestApproval$;
    this.huntApprovalRoute$ = this.huntApprovalLocalStore.huntApprovalRoute$;
    this.approvalParams$ = new BehaviorSubject<ApprovalParams | null>(null);
    this.requestApprovalStatus$ =
      this.huntApprovalLocalStore.requestApprovalStatus$;
    this.titleControl = new FormControl('', {updateOn: 'change'});
    this.ngOnDestroy = observeOnDestroy(this);
    this.huntsOverviewRoute = ['/hunts'];
    this.hasOrigin$ = combineLatest([
      this.flowWithDescriptor$,
      this.originalHunt$,
    ]).pipe(
      map(([flowDesc, hunt]) => {
        if (!flowDesc && !hunt) {
          return false;
        }
        return true;
      }),
      startWith(false),
    );
    this.canCreateHunt$ = this.hasOrigin$;
    this.route.queryParams
      .pipe(takeUntil(this.ngOnDestroy.triggered$))
      .subscribe((params) => {
        const clientId = params['clientId'];
        const flowId = params['flowId'];
        const huntId = params['huntId'];

        if (clientId && flowId) {
          this.newHuntLocalStore.selectOriginalFlow(clientId, flowId);
          this.hasOriginInput = true;
          this.originalFlowRef = {clientId, flowId};
          return;
        }

        if (huntId) {
          this.newHuntLocalStore.selectOriginalHunt(huntId);
          this.hasOriginInput = true;
          this.originalHuntRef = {huntId};
          return;
        }

        this.hasOriginInput = false;
      });

    combineLatest([this.approvalParams$, this.huntId$])
      .pipe(
        takeUntil(this.ngOnDestroy.triggered$),
        filter(
          ([approvalParams, huntId]) =>
            isNonNull(approvalParams) && isNonNull(huntId),
        ),
      )
      .subscribe(([approvalParams, huntId]) => {
        this.huntApprovalLocalStore.requestHuntApproval({
          huntId: huntId!,
          approvers: approvalParams!.approvers,
          reason: approvalParams!.reason,
          cc: approvalParams!.cc,
        });
      });
    combineLatest([this.huntApprovalRequired$, this.huntId$])
      .pipe(
        takeUntil(this.ngOnDestroy.triggered$),
        filter(
          ([isRequired, huntId]) => isNonNull(isRequired) && isNonNull(huntId),
        ),
        switchMap(([isRequired, huntId]) => {
          return isRequired
            ? this.requestApprovalStatus$.pipe(
                filter(isNonNull),
                // tslint:disable-next-line:enforce-name-casing
                map((_) => {
                  return huntId;
                }),
              )
            : of(huntId);
        }),
      )
      .subscribe((huntId) => {
        this.router.navigate([`/hunts/${huntId}`]);
      });

    this.newHuntLocalStore.originalHunt$
      .pipe(
        tap((v) => {
          if (isNull(v)) {
            return;
          }

          this.titleControl.setValue(getHuntTitle(v) + ' (copy)');

          if (v.clientRuleSet) {
            this.clientsForm.setFormState(v.clientRuleSet);
          }
          if (v.safetyLimits) {
            this.paramsForm.setFormState(v.safetyLimits);
          }
          if (v.outputPlugins) {
            this.outputPluginsForm.setFormState(v.outputPlugins);
          }
        }),
      )
      .subscribe();

    this.newHuntLocalStore.flowWithDescriptor$
      .pipe(
        tap((fwd) => {
          if (fwd?.flow) {
            this.originalFlowRef = {
              clientId: fwd.flow.clientId,
              flowId: fwd.flow.flowId,
            };
          }
        }),
      )
      .subscribe();

    this.titleControl.valueChanges.subscribe((v) => {
      this.newHuntLocalStore.setCurrentDescription(v ?? '');
    });
  }

  runHunt() {
    const safetyLimits = this.paramsForm.buildSafetyLimits();
    const rules = this.clientsForm.buildRules();
    const outputPlugins = this.outputPluginsForm.buildOutputPlugins();
    this.newHuntLocalStore.runHunt(
      this.titleControl.value ?? '',
      safetyLimits,
      rules,
      outputPlugins,
    );
    // approval's submitRequest() method will trigger an emits of parameters
    // needed for request approval to new_hunt component. This is handled in
    // requestHuntApproval() method in new_hunt.
    if (this.approvalCard) {
      this.approvalCard.submitRequest();
    }
  }

  requestHuntApproval(approvalParams: ApprovalParams) {
    this.approvalParams$.next(approvalParams);
  }
}
