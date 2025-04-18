import {ErrorHandler, NgModule} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatIconModule, MatIconRegistry} from '@angular/material/icon';
import {MatSidenavModule} from '@angular/material/sidenav';
import {MatSnackBarModule} from '@angular/material/snack-bar';
import {MatTabsModule} from '@angular/material/tabs';
import {MatToolbarModule} from '@angular/material/toolbar';
import {MatTooltipModule} from '@angular/material/tooltip';
import {BrowserModule} from '@angular/platform-browser';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {RouteReuseStrategy} from '@angular/router';

import {ClientPageModule} from '../../components/client_page/client_page_module';
import {ClientSearchModule} from '../../components/client_search/module';
import {HomeModule} from '../../components/home/module';
import {HuntApprovalPageModule} from '../../components/hunt/hunt_approval_page/hunt_approval_page_module';
import {HuntHelpModule} from '../../components/hunt/hunt_help/module';
import {HuntPageModule} from '../../components/hunt/hunt_page/module';
import {NewHuntModule} from '../../components/hunt/new_hunt/module';
import {UserMenuModule} from '../../components/user_menu/module';
import {ApiModule} from '../../lib/api/module';
import {SameComponentRouteReuseStrategy} from '../../lib/routing';
import {ApprovalPageModule} from '../approval_page/approval_page_module';
import {FileDetailsModule} from '../file_details/file_details_module';
import {SnackBarErrorHandler} from '../helpers/error_snackbar/error_handler';
import {ErrorSnackBarModule} from '../helpers/error_snackbar/error_snackbar_module';
import {HuntArguments} from '../hunt/hunt_arguments/hunt_arguments';
import {HuntFlowArguments} from '../hunt/hunt_flow_arguments/hunt_flow_arguments';

import {App} from './app';
import {NotFoundPage} from './not_found_page';
import {AppRoutingModule} from './routing';

const ANGULAR_MATERIAL_MODULES = [
  // TODO: re-enable clang format when solved.
  // prettier-ignore
  // keep-sorted start block=yes
  MatButtonModule,
  MatIconModule,
  MatSidenavModule,
  MatSnackBarModule,
  MatTabsModule,
  MatToolbarModule,
  MatTooltipModule,
  // keep-sorted end
];

const GRR_MODULES = [
  // TODO: re-enable clang format when solved.
  // prettier-ignore
  // keep-sorted start block=yes
  ApiModule,
  ApprovalPageModule,
  ClientPageModule,
  ClientSearchModule,
  ErrorSnackBarModule,
  FileDetailsModule,
  HomeModule,
  HuntApprovalPageModule,
  HuntArguments,
  HuntFlowArguments,
  HuntHelpModule,
  HuntPageModule,
  NewHuntModule,
  UserMenuModule,
  // keep-sorted end
];

/**
 * The main application module.
 */
@NgModule({
  declarations: [App, NotFoundPage],
  imports: [
    BrowserModule,
    BrowserAnimationsModule,
    ...ANGULAR_MATERIAL_MODULES,
    ...GRR_MODULES,
    // Should be the last to make sure all module-specific routes are
    // already registered by the time it's imported.
    AppRoutingModule,
  ],
  providers: [
    {provide: RouteReuseStrategy, useClass: SameComponentRouteReuseStrategy},
    // Register SnackBarErrorHandler as default error handler for whole app.
    {provide: ErrorHandler, useClass: SnackBarErrorHandler},
  ],
  bootstrap: [App],
  exports: [NotFoundPage],
})
export class AppModule {
  constructor(iconRegistry: MatIconRegistry) {
    iconRegistry.setDefaultFontSetClass('material-icons-outlined');
  }
}

/**
 * The main application module with dev tools support. It enables integration
 * with Chrome's Redux Devltools extension.
 */
@NgModule({
  imports: [AppModule],
  providers: [],
  bootstrap: [App],
})
export class DevAppModule {}
