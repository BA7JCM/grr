import {Injectable} from '@angular/core';
import {ComponentStore} from '@ngrx/component-store';
import {Observable, of} from 'rxjs';
import {
  filter,
  map,
  shareReplay,
  switchMap,
  switchMapTo,
  tap,
} from 'rxjs/operators';

import {ApiUiConfig} from '../lib/api/api_interfaces';
import {HttpApiService} from '../lib/api/http_api_service';
import {translateArtifactDescriptor} from '../lib/api_translation/artifact';
import {getApiClientLabelName} from '../lib/api_translation/client';
import {
  safeTranslateBinary,
  translateFlowDescriptor,
} from '../lib/api_translation/flow';
import {translateOutputPluginDescriptor} from '../lib/api_translation/output_plugin';
import {cacheLatest} from '../lib/cache';
import {ApprovalConfig} from '../lib/models/client';
import {
  ArtifactDescriptor,
  ArtifactDescriptorMap,
  Binary,
  FlowDescriptor,
  FlowDescriptorMap,
} from '../lib/models/flow';
import {
  OutputPluginDescriptor,
  OutputPluginDescriptorMap,
} from '../lib/models/output_plugin';
import {isNonNull} from '../lib/preconditions';

/** The state of the Config. */
export interface ConfigState {
  readonly flowDescriptors?: FlowDescriptorMap;
  readonly artifactDescriptors?: ArtifactDescriptorMap;
  readonly outputPluginDescriptors?: OutputPluginDescriptorMap;
  readonly approvalConfig?: ApprovalConfig;
  readonly uiConfig?: ApiUiConfig;
  readonly clientsLabels?: readonly string[];
  readonly binaries?: readonly Binary[];
  readonly webAuthType?: string;
  readonly exportCommandPrefix?: string;
}

/** ComponentStore implementation for the config store. */
class ConfigComponentStore extends ComponentStore<ConfigState> {
  constructor(private readonly httpApiService: HttpApiService) {
    super({});
  }

  private readonly updateFlowDescriptors = this.updater<
    readonly FlowDescriptor[]
  >((state, descriptors) => {
    return {
      ...state,
      flowDescriptors: new Map(descriptors.map((fd) => [fd.name, fd])),
    };
  });

  private readonly updateArtifactDescriptors = this.updater<
    readonly ArtifactDescriptor[]
  >((state, descriptors) => {
    return {
      ...state,
      artifactDescriptors: new Map(descriptors.map((ad) => [ad.name, ad])),
    };
  });

  private readonly updateOutputPluginDescriptors = this.updater<
    readonly OutputPluginDescriptor[]
  >((state, descriptors) => {
    return {
      ...state,
      outputPluginDescriptors: new Map(
        descriptors.map((opd) => [opd.name, opd]),
      ),
    };
  });

  private readonly updateApprovalConfig = this.updater<ApprovalConfig>(
    (state, approvalConfig) => {
      return {...state, approvalConfig};
    },
  );

  private readonly updateClientsLabels = this.updater<string[]>(
    (state, clientsLabels) => {
      return {...state, clientsLabels};
    },
  );

  private readonly listFlowDescriptors = this.effect<void>((obs$) =>
    obs$.pipe(
      switchMap(() => this.httpApiService.listFlowDescriptors()),
      map((apiDescriptors) => apiDescriptors.map(translateFlowDescriptor)),
      tap((descriptors) => {
        this.updateFlowDescriptors(descriptors);
      }),
    ),
  );

  private readonly listArtifactDescriptors = this.effect<void>((obs$) =>
    obs$.pipe(
      switchMap(() => this.httpApiService.listArtifactDescriptors()),
      cacheLatest('listArtifactDescriptors'),
      map((apiDescriptors) => apiDescriptors.map(translateArtifactDescriptor)),
      tap((descriptors) => {
        this.updateArtifactDescriptors(descriptors);
      }),
    ),
  );

  private readonly listOutputPluginDescriptors = this.effect<void>((obs$) =>
    obs$.pipe(
      switchMap(() => this.httpApiService.listOutputPluginDescriptors()),
      cacheLatest('listOutputPluginDescriptors'),
      map((apiDescriptors) =>
        apiDescriptors.map(translateOutputPluginDescriptor),
      ),
      tap((descriptors) => {
        this.updateOutputPluginDescriptors(descriptors);
      }),
    ),
  );

  private readonly listBinaries = this.effect<void>((obs$) =>
    obs$.pipe(
      switchMap(() => this.httpApiService.listBinaries()),
      map((res) =>
        (res.items ?? []).map(safeTranslateBinary).filter(isNonNull),
      ),
      tap((binaries) => {
        this.patchState({binaries});
      }),
    ),
  );

  private readonly fetchApprovalConfig = this.effect<void>((obs$) =>
    obs$.pipe(
      switchMap(() => this.httpApiService.fetchApprovalConfig()),
      tap((approvalConfig) => {
        this.updateApprovalConfig(approvalConfig);
      }),
    ),
  );

  private readonly fetchClientsLabels = this.effect<void>((obs$) =>
    obs$.pipe(
      switchMapTo(this.httpApiService.fetchAllClientsLabels()),
      /**
       * When fetching all labels the owner is not set in the API
       * implementation, so we extract only the label names
       */
      map((apiClientsLabels) => apiClientsLabels.map(getApiClientLabelName)),
      tap((clientsLabels) => {
        this.updateClientsLabels(clientsLabels);
      }),
    ),
  );

  /** An observable emitting available flow descriptors. */
  readonly flowDescriptors$ = of(undefined).pipe(
    // Ensure that the query is done on subscription.
    tap(() => {
      this.listFlowDescriptors();
    }),
    switchMap(() => this.select((state) => state.flowDescriptors)),
    filter(isNonNull),
    shareReplay(1), // Ensure that the query is done just once.
  );

  /** An observable emitting the approval configuration. */
  readonly approvalConfig$ = of(undefined).pipe(
    // Ensure that the query is done on subscription.
    tap(() => {
      this.fetchApprovalConfig();
    }),
    switchMap(() => this.select((state) => state.approvalConfig)),
    filter(isNonNull),
    shareReplay(1), // Ensure that the query is done just once.
  );

  private readonly updateUiConfig = this.updater<ApiUiConfig>(
    (state, uiConfig) => {
      return {...state, uiConfig};
    },
  );

  private readonly fetchUiConfig = this.effect<void>((obs$) =>
    obs$.pipe(
      switchMap(() => this.httpApiService.fetchUiConfig()),
      tap((uiConfig) => {
        this.updateUiConfig(uiConfig);
      }),
    ),
  );

  /** An observable emitting available UI configuration. */
  readonly uiConfig$ = of(undefined).pipe(
    // Ensure that the query is done on subscription.
    tap(() => {
      this.fetchUiConfig();
    }),
    switchMap(() => this.select((state) => state.uiConfig)),
    filter(isNonNull),
    shareReplay(1), // Ensure that the query is done just once.
  );

  /** An observable emitting a list of all clients labels. */
  readonly clientsLabels$ = of(undefined).pipe(
    tap(() => {
      this.fetchClientsLabels();
    }),
    switchMapTo(this.select((state) => state.clientsLabels)),
    filter(
      (clientsLabels): clientsLabels is string[] => clientsLabels !== undefined,
    ),
  );

  /** An observable emitting available artifact descriptors. */
  readonly artifactDescriptors$ = of(undefined).pipe(
    // Ensure that the query is done on subscription.
    tap(() => {
      this.listArtifactDescriptors();
    }),
    switchMap(() => this.select((state) => state.artifactDescriptors)),
    filter(isNonNull),
    shareReplay(1), // Ensure that the query is done just once.
  );

  /** An observable emitting available output plugin descriptors. */
  readonly outputPluginDescriptors$ = of(undefined).pipe(
    // Ensure that the query is done on subscription.
    tap(() => {
      this.listOutputPluginDescriptors();
    }),
    switchMap(() => this.select((state) => state.outputPluginDescriptors)),
    filter(isNonNull),
    shareReplay(1), // Ensure that the query is done just once.
  );

  readonly binaries$ = of(undefined).pipe(
    // Ensure that the query is done on subscription.
    tap(() => {
      this.listBinaries();
    }),
    switchMap(() => this.select((state) => state.binaries)),
    filter(isNonNull),
    shareReplay(1), // Ensure that the query is done just once.
  );

  private readonly updateWebAuthType = this.updater<string>(
    (state, webAuthType) => {
      return {...state, webAuthType};
    },
  );

  private readonly fetchWebAuthType = this.effect<void>((obs$) =>
    obs$.pipe(
      switchMap(() => this.httpApiService.fetchWebAuthType()),
      tap((webAuthType) => {
        this.updateWebAuthType(webAuthType);
      }),
    ),
  );

  /** An observable emitting available webAuthType. */
  readonly webAuthType$ = of(undefined).pipe(
    // Ensure that the query is done on subscription.
    tap(() => {
      this.fetchWebAuthType();
    }),
    switchMap(() => this.select((state) => state.webAuthType)),
    filter(isNonNull),
    shareReplay(1), // Ensure that the query is done just once.
  );

  private readonly updateExportCommandPrefix = this.updater<string>(
    (state, exportCommandPrefix) => {
      return {...state, exportCommandPrefix};
    },
  );

  private readonly fetchExportCommandPrefix = this.effect<void>((obs$) =>
    obs$.pipe(
      switchMap(() => this.httpApiService.fetchExportCommandPrefix()),
      tap((exportCommandPrefix) => {
        this.updateExportCommandPrefix(exportCommandPrefix);
      }),
    ),
  );

  /** An observable emitting available exportCommandPrefix. */
  readonly exportCommandPrefix$ = of(undefined).pipe(
    // Ensure that the query is done on subscription.
    tap(() => {
      this.fetchExportCommandPrefix();
    }),
    switchMap(() => this.select((state) => state.exportCommandPrefix)),
    filter(isNonNull),
    shareReplay(1), // Ensure that the query is done just once.
  );
}

/** Store to retrieve general purpose configuration and backend data. */
@Injectable({
  providedIn: 'root',
})
export class ConfigGlobalStore {
  constructor(private readonly httpApiService: HttpApiService) {
    this.store = new ConfigComponentStore(this.httpApiService);
    this.flowDescriptors$ = this.store.flowDescriptors$;
    this.approvalConfig$ = this.store.approvalConfig$;
    this.uiConfig$ = this.store.uiConfig$;
    this.clientsLabels$ = this.store.clientsLabels$;
    this.artifactDescriptors$ = this.store.artifactDescriptors$;
    this.binaries$ = this.store.binaries$;
    this.outputPluginDescriptors$ = this.store.outputPluginDescriptors$;
    this.webAuthType$ = this.store.webAuthType$;
    this.exportCommandPrefix$ = this.store.exportCommandPrefix$;
  }

  private readonly store;

  /** An observable emitting available flow descriptors. */
  readonly flowDescriptors$: Observable<FlowDescriptorMap>;

  /** An observable emitting the approval configuration. */
  readonly approvalConfig$: Observable<ApprovalConfig>;

  /** An observable emitting the UI configuration. */
  readonly uiConfig$: Observable<ApiUiConfig>;

  /** An observable emitting a list of all clients labels. */
  readonly clientsLabels$: Observable<string[]>;

  readonly artifactDescriptors$: Observable<ArtifactDescriptorMap>;

  readonly binaries$: Observable<readonly Binary[]>;

  readonly outputPluginDescriptors$: Observable<OutputPluginDescriptorMap>;

  readonly webAuthType$: Observable<string>;

  readonly exportCommandPrefix$: Observable<string>;
}
